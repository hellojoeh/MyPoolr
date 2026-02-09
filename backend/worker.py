#!/usr/bin/env python3
"""Celery worker management script with monitoring and health checks."""

import os
import sys
import time
import signal
import logging
import subprocess
from typing import Dict, List, Optional
from celery_app import celery_app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkerManager:
    """Manages Celery workers with monitoring and health checks."""
    
    def __init__(self):
        self.workers: Dict[str, subprocess.Popen] = {}
        self.running = True
        
    def start_worker(self, queue: str, concurrency: int = 2, loglevel: str = "info") -> bool:
        """Start a Celery worker for a specific queue."""
        try:
            worker_name = f"worker_{queue}"
            
            # Build worker command
            cmd = [
                sys.executable, "-m", "celery",
                "worker",
                "-A", "celery_app",
                "-Q", queue,
                "-n", f"{worker_name}@%h",
                "--concurrency", str(concurrency),
                "--loglevel", loglevel,
                "--without-gossip",
                "--without-mingle",
                "--without-heartbeat"
            ]
            
            # Start worker process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.workers[queue] = process
            logger.info(f"Started worker for queue '{queue}' with PID {process.pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start worker for queue '{queue}': {e}")
            return False
    
    def stop_worker(self, queue: str) -> bool:
        """Stop a specific worker."""
        if queue not in self.workers:
            logger.warning(f"No worker found for queue '{queue}'")
            return False
            
        try:
            process = self.workers[queue]
            process.terminate()
            
            # Wait for graceful shutdown
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                logger.warning(f"Worker for queue '{queue}' didn't stop gracefully, killing...")
                process.kill()
                process.wait()
            
            del self.workers[queue]
            logger.info(f"Stopped worker for queue '{queue}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop worker for queue '{queue}': {e}")
            return False
    
    def restart_worker(self, queue: str) -> bool:
        """Restart a specific worker."""
        logger.info(f"Restarting worker for queue '{queue}'")
        self.stop_worker(queue)
        time.sleep(2)  # Brief pause
        return self.start_worker(queue)
    
    def check_worker_health(self, queue: str) -> bool:
        """Check if a worker is healthy."""
        if queue not in self.workers:
            return False
            
        process = self.workers[queue]
        return process.poll() is None  # None means process is still running
    
    def monitor_workers(self):
        """Monitor worker health and restart if needed."""
        while self.running:
            try:
                for queue in list(self.workers.keys()):
                    if not self.check_worker_health(queue):
                        logger.warning(f"Worker for queue '{queue}' is unhealthy, restarting...")
                        self.restart_worker(queue)
                
                time.sleep(30)  # Check every 30 seconds
                
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                self.shutdown()
                break
            except Exception as e:
                logger.error(f"Error in worker monitoring: {e}")
                time.sleep(10)
    
    def start_all_workers(self):
        """Start workers for all queues."""
        queues_config = {
            "defaults": {"concurrency": 4, "loglevel": "info"},  # High priority, more workers
            "rotation": {"concurrency": 2, "loglevel": "info"},
            "reminders": {"concurrency": 2, "loglevel": "info"},
            "default": {"concurrency": 1, "loglevel": "info"},
        }
        
        for queue, config in queues_config.items():
            self.start_worker(queue, **config)
    
    def shutdown(self):
        """Gracefully shutdown all workers."""
        self.running = False
        logger.info("Shutting down all workers...")
        
        for queue in list(self.workers.keys()):
            self.stop_worker(queue)
        
        logger.info("All workers stopped")
    
    def get_worker_stats(self) -> Dict[str, Dict]:
        """Get statistics for all workers."""
        stats = {}
        
        for queue, process in self.workers.items():
            stats[queue] = {
                "pid": process.pid,
                "running": process.poll() is None,
                "queue": queue
            }
        
        return stats


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    global worker_manager
    if worker_manager:
        worker_manager.shutdown()
    sys.exit(0)


def main():
    """Main worker management function."""
    global worker_manager
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create worker manager
    worker_manager = WorkerManager()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "start":
            logger.info("Starting all workers...")
            worker_manager.start_all_workers()
            worker_manager.monitor_workers()
            
        elif command == "stop":
            logger.info("Stopping all workers...")
            worker_manager.shutdown()
            
        elif command == "status":
            stats = worker_manager.get_worker_stats()
            print("Worker Status:")
            for queue, info in stats.items():
                status = "Running" if info["running"] else "Stopped"
                print(f"  {queue}: {status} (PID: {info['pid']})")
                
        elif command == "health":
            # Run health check task
            try:
                result = celery_app.send_task("health_check")
                response = result.get(timeout=10)
                print(f"Health check result: {response}")
            except Exception as e:
                print(f"Health check failed: {e}")
                sys.exit(1)
                
        else:
            print("Usage: python worker.py [start|stop|status|health]")
            sys.exit(1)
    else:
        print("Usage: python worker.py [start|stop|status|health]")
        sys.exit(1)


if __name__ == "__main__":
    main()