"""Auto switch and watchdog for proxy nodes based on health checks."""

import logging
import time
import threading

logger = logging.getLogger(__name__)


class AutoSwitch:
    """Automatically switch to better nodes based on health checks, with an
    independent watchdog that keeps the proxy process alive.

    The monitor loop runs both subsystems on their own intervals:
      * watchdog  -- restarts the proxy process if it dies (independent of
                     auto_switch.enabled, controlled by watchdog.enabled).
      * auto_switch -- switches to a better node based on latency.

    Either subsystem can be enabled/disabled independently via settings.json.
    The loop tick interval is the shorter of the two so each subsystem can
    run on its own schedule.
    """

    def __init__(self, config, node_manager, health_checker, proxy_manager):
        self.config = config
        self.node_manager = node_manager
        self.health_checker = health_checker
        self.proxy_manager = proxy_manager
        self._running = False
        self._thread = None
        # Subsystem enable flags and intervals (populated in start())
        self._watchdog_enabled = False
        self._auto_switch_enabled = False
        self._watchdog_interval = 30
        self._auto_switch_interval = 300
        self._tick_interval = 30
        self._last_watchdog = 0.0
        self._last_auto_switch = 0.0

    def start(self) -> None:
        """Start monitoring (watchdog and/or auto-switch).

        The monitor starts as long as at least one subsystem is enabled.
        The watchdog is independent of auto_switch, so the proxy will be
        kept alive even when auto-switch is disabled.
        """
        if self._running:
            logger.warning('Monitor is already running')
            return

        settings = self.config.load_config('settings.json')
        auto_switch_cfg = settings.get('auto_switch', {})
        watchdog_cfg = settings.get('watchdog', {})

        self._auto_switch_enabled = auto_switch_cfg.get('enabled', False)
        # Watchdog defaults to enabled for safety
        self._watchdog_enabled = watchdog_cfg.get('enabled', True)

        if not self._auto_switch_enabled and not self._watchdog_enabled:
            logger.info('Both auto-switch and watchdog are disabled, skipping monitor')
            return

        self._auto_switch_interval = auto_switch_cfg.get('interval', 300)
        self._watchdog_interval = watchdog_cfg.get('interval', 30)

        # The loop tick is the shorter interval so each subsystem can still
        # honour its own (longer) schedule.
        intervals = []
        if self._watchdog_enabled:
            intervals.append(self._watchdog_interval)
        if self._auto_switch_enabled:
            intervals.append(self._auto_switch_interval)
        self._tick_interval = min(intervals) if intervals else 30

        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(
            f'Monitor started (tick: {self._tick_interval}s, '
            f'watchdog: {self._watchdog_enabled}@{self._watchdog_interval}s, '
            f'auto-switch: {self._auto_switch_enabled}@{self._auto_switch_interval}s)'
        )

        # Eagerly run a watchdog check on the main thread so the proxy is
        # (re)started immediately on launch/launchd boot, without depending
        # on the background thread's first tick. Update _last_watchdog so the
        # loop does not re-trigger it right away.
        if self._watchdog_enabled:
            try:
                self._watchdog_check()
                self._last_watchdog = time.time()
            except Exception as e:
                logger.error(f'Initial watchdog check failed: {e}')

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info('Monitor stopped')

    def _monitor_loop(self) -> None:
        """Main monitoring loop running watchdog and auto-switch on their own intervals."""
        while self._running:
            now = time.time()
            try:
                # Watchdog tick
                if self._watchdog_enabled and (now - self._last_watchdog) >= self._watchdog_interval:
                    self._watchdog_check()
                    self._last_watchdog = time.time()

                # Auto-switch tick
                if self._auto_switch_enabled and (now - self._last_auto_switch) >= self._auto_switch_interval:
                    self._check_and_switch()
                    self._last_auto_switch = time.time()
            except Exception as e:
                logger.error(f'Monitor loop error: {e}')
            time.sleep(self._tick_interval)

    def _watchdog_check(self) -> None:
        """Watchdog: ensure the proxy process is alive, restart with retries if not."""
        if self.proxy_manager.is_running():
            return

        logger.warning('Proxy process is not running, watchdog restarting...')

        settings = self.config.load_config('settings.json')
        watchdog_cfg = settings.get('watchdog', {})
        max_retries = watchdog_cfg.get('max_retries', 3)
        retry_delay = watchdog_cfg.get('retry_delay', 5)

        node_id = self.node_manager.get_default_node()
        if not node_id:
            logger.error('Watchdog: no default node available for restart')
            return

        for attempt in range(1, max_retries + 1):
            try:
                self.proxy_manager.start(node_id)
                logger.info(f'Watchdog restarted proxy (node: {node_id}, attempt: {attempt}/{max_retries})')
                return
            except Exception as e:
                logger.error(f'Watchdog restart attempt {attempt}/{max_retries} failed: {e}')
                if attempt < max_retries:
                    time.sleep(retry_delay)
        logger.error(f'Watchdog exhausted {max_retries} retries; will try again next interval')

    def _check_and_switch(self) -> None:
        """Check nodes and switch if needed."""
        settings = self.config.load_config('settings.json')
        threshold = settings.get('auto_switch', {}).get('threshold', 200)

        # Get all active nodes
        nodes = self.node_manager.list_nodes()
        active_nodes = [n for n in nodes if n.get('status') == 'active']
        if not active_nodes:
            return

        node_ids = [n['id'] for n in active_nodes]

        # Set node manager for health checker
        self.health_checker.set_node_manager(self.node_manager)

        # Batch check
        results = self.health_checker.batch_check(node_ids)
        results = self.health_checker.sort_by_latency(results)

        if not results:
            return

        # Find best node
        best = results[0]
        if best.get('latency', -1) <= 0:
            logger.warning('No healthy nodes found')
            return

        current_node = self.node_manager.get_default_node()
        if best['id'] == current_node:
            return

        # Switch if current node latency exceeds threshold
        current_result = next((r for r in results if r['id'] == current_node), None)
        if current_result:
            current_latency = current_result.get('latency', float('inf'))
            if current_latency > threshold and best['latency'] < current_latency:
                logger.info(f'Auto switching from {current_node} ({current_latency}ms) '
                            f'to {best["id"]} ({best["latency"]}ms)')
                self.proxy_manager.stop()
                self.proxy_manager.start(best['id'])
                self.node_manager.set_default_node(best['id'])

    def manual_switch(self, node_id: str) -> bool:
        """Manually trigger a switch to a specific node."""
        if not self.proxy_manager.is_running():
            logger.warning('Proxy is not running')
            return False

        self.proxy_manager.stop()
        self.proxy_manager.start(node_id)
        self.node_manager.set_default_node(node_id)
        logger.info(f'Manually switched to {node_id}')
        return True
