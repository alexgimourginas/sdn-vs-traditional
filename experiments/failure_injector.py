"""Failure injector — Module 5."""

import threading
import time


def inject_link_failure(network, a: str, b: str, at: float,
                        restore_at: float = None, logger=None, experiment: str = ""):
    """Schedule a link failure (and optional restore) using wall-clock time."""

    def _fail():
        time.sleep(at)
        network.fail_link(a, b)
        if logger:
            logger.log_event(experiment, at, "link_failure", {"a": a, "b": b})
        if restore_at is not None:
            def _restore():
                time.sleep(restore_at - at)
                network.restore_link(a, b)
                if logger:
                    logger.log_event(experiment, restore_at, "link_restore", {"a": a, "b": b})
            threading.Thread(target=_restore, daemon=True).start()

    threading.Thread(target=_fail, daemon=True).start()


def inject_node_failure(network, node_id: str, at: float,
                        logger=None, experiment: str = ""):
    def _fail():
        time.sleep(at)
        network.fail_node(node_id)
        if logger:
            logger.log_event(experiment, at, "node_failure", {"node": node_id})

    threading.Thread(target=_fail, daemon=True).start()


def inject_link_degradation(network, a: str, b: str,
                             start_at: float, end_at: float,
                             max_loss: float = 0.5,
                             steps: int = 10,
                             logger=None, experiment: str = ""):
    """Gradually increase packet loss on a link from 0 to max_loss over time."""

    def _degrade():
        time.sleep(start_at)
        link = network.get_link(a, b)
        if link is None:
            return
        step_interval = (end_at - start_at) / steps
        for i in range(1, steps + 1):
            loss = max_loss * (i / steps)
            link.set_loss_rate(loss)
            if logger:
                logger.log_event(experiment, start_at + i * step_interval,
                                 "link_degradation", {"a": a, "b": b, "loss_rate": loss})
            time.sleep(step_interval)

    threading.Thread(target=_degrade, daemon=True).start()


def inject_congestion(network, a: str, b: str,
                      src_node, dst_id: str,
                      start_at: float, end_at: float,
                      rate_pps: float = 200,
                      logger=None, experiment: str = ""):
    """Flood a link with background traffic to simulate congestion."""
    from experiments.traffic_gen import cbr

    def _congest():
        time.sleep(start_at)
        if logger:
            logger.log_event(experiment, start_at, "congestion_start", {"a": a, "b": b})
        cbr(src_node, dst_id, rate_pps=rate_pps, duration=end_at - start_at,
            flow_id="congestion_bg", size=1500)

    threading.Thread(target=_congest, daemon=True).start()


def inject_controller_failure(sdn_network, at: float, restore_at: float = None,
                               logger=None, experiment: str = ""):
    """Kill (and optionally revive) the SDN controller."""

    def _fail():
        time.sleep(at)
        sdn_network.fail_controller()
        if logger:
            logger.log_event(experiment, at, "controller_failure", {})
        if restore_at is not None:
            def _restore():
                time.sleep(restore_at - at)
                sdn_network.revive_controller()
                if logger:
                    logger.log_event(experiment, restore_at, "controller_restore", {})
            threading.Thread(target=_restore, daemon=True).start()

    threading.Thread(target=_fail, daemon=True).start()
