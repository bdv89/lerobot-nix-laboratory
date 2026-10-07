"""
Wrapper for LeRobot commands to be used by the GUI.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def disable_usb_autosuspend():
    """Disable USB autosuspend for serial and camera devices to prevent signal loss."""
    for dev in Path("/sys/bus/usb/devices/").iterdir():
        product_file = dev / "product"
        control_file = dev / "power" / "control"
        if product_file.exists() and control_file.exists():
            try:
                product = product_file.read_text().strip()
                if any(k in product.lower() for k in ("serial", "cam")):
                    control_file.write_text("on")
                    print(f"USB autosuspend disabled: {product}")
            except PermissionError:
                print(f"USB autosuspend: permission denied for {product_file} (run as root or add udev rule)")
            except Exception:
                pass


class LeRobotWrapper:
    """Wrapper class for executing LeRobot commands."""

    def __init__(self, workdir: Optional[Path] = None):
        """LeRobot vient de l'environnement Python (Nix) ; workdir recoit outputs/ et trained/."""
        self.workdir = Path(workdir or os.environ.get("LEROBOT_WORKDIR", Path.home() / "lerobot"))
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.supports_episode_time_limit = self._detect_episode_time_support()

        # Local dataset cache
        self._hf_cache = Path.home() / ".cache" / "huggingface" / "lerobot"

    def _run(self, cmd: list[str]) -> subprocess.Popen:
        """Launch a subprocess, auto-confirming calibration prompts."""
        print(f"EXECUTING: {' '.join(cmd)}")
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=self.workdir,
        )
        # Send newlines to auto-confirm calibration prompts
        # (follower + leader both ask "Press ENTER to use calibration file")
        import threading

        def _send_confirms():
            import time
            try:
                for _ in range(5):
                    time.sleep(2)
                    if proc.poll() is not None:
                        return
                    proc.stdin.write('\n')
                    proc.stdin.flush()
            except Exception:
                pass

        threading.Thread(target=_send_confirms, daemon=True).start()
        return proc

    def _dataset_can_resume(self, dataset_repo_id: str) -> bool:
        """Check if a local dataset exists and has episodes (can be resumed)."""
        ds_path = self._hf_cache / dataset_repo_id
        if not ds_path.exists():
            return False
        # Must have meta/info.json AND episode data files
        info_path = ds_path / "meta" / "info.json"
        if not info_path.exists():
            return False
        # Check for episode parquet files in data/
        data_dir = ds_path / "data"
        if not data_dir.exists():
            return False
        parquet_files = list(data_dir.rglob("*.parquet"))
        return len(parquet_files) > 0

    def _dataset_exists_but_empty(self, dataset_repo_id: str) -> bool:
        """Check if a dataset dir exists but has no episodes."""
        ds_path = self._hf_cache / dataset_repo_id
        return ds_path.exists() and not self._dataset_can_resume(dataset_repo_id)

    @staticmethod
    def _detect_episode_time_support() -> bool:
        """Return True if current LeRobot CLI supports episode_time_s override."""
        try:
            from lerobot.scripts.lerobot_record import DatasetRecordConfig  # type: ignore

            annotations = getattr(DatasetRecordConfig, "__annotations__", {})
            return "episode_time_s" in annotations
        except Exception:
            return False

    def record(
        self,
        robot_type: str,
        robot_port: str,
        dataset_repo_id: str,
        num_episodes: int = 1,
        single_task: str = "",
        episode_time_s: Optional[float] = None,
        cameras_config: Optional[dict] = None,
        teleop_type: Optional[str] = None,
        teleop_port: Optional[str] = None,
        robot_id: Optional[str] = None,
        teleop_id: Optional[str] = None,
        display_data: bool = False,
        push_to_hub: bool = False,
        policy_path: Optional[str] = None,
    ) -> subprocess.Popen:
        """Start recording episodes. Auto-detects resume vs create.

        With policy_path, the policy drives the robot (dataset name must start with 'eval_').
        """
        import shutil

        # Auto-detect resume: if dataset has episodes, resume; if empty dir, clean up
        use_resume = False
        if self._dataset_can_resume(dataset_repo_id):
            use_resume = True
            print(f"Dataset {dataset_repo_id} has episodes, resuming.")
        elif self._dataset_exists_but_empty(dataset_repo_id):
            ds_path = self._hf_cache / dataset_repo_id
            print(f"Dataset {dataset_repo_id} is empty/incomplete, removing.")
            shutil.rmtree(ds_path)

        cmd = [
            sys.executable,
            "-m", "lerobot.scripts.lerobot_record",
            f"--robot.type={robot_type}",
            f"--robot.port={robot_port}",
            f"--dataset.repo_id={dataset_repo_id}",
            f"--dataset.num_episodes={num_episodes}",
            f"--display_data={str(display_data).lower()}",
            f"--dataset.push_to_hub={str(push_to_hub).lower()}",
        ]

        if use_resume:
            cmd.append("--resume=true")

        if robot_id:
            cmd.append(f"--robot.id={robot_id}")

        if single_task:
            cmd.append(f"--dataset.single_task={single_task}")

        if episode_time_s is not None and self.supports_episode_time_limit:
            cmd.append(f"--dataset.episode_time_s={episode_time_s}")
        elif episode_time_s is not None and not self.supports_episode_time_limit:
            print("⚠️ LeRobot CLI sans support de --dataset.episode_time_s, valeur ignorée.")

        if cameras_config:
            import json
            cameras_str = json.dumps(cameras_config)
            cmd.append(f"--robot.cameras={cameras_str}")

        if teleop_type:
            cmd.append(f"--teleop.type={teleop_type}")

        if teleop_port:
            cmd.append(f"--teleop.port={teleop_port}")

        if teleop_id:
            cmd.append(f"--teleop.id={teleop_id}")

        if policy_path:
            cmd.append(f"--policy.path={policy_path}")

        return self._run(cmd)

    def replay(
        self,
        robot_type: str,
        robot_port: str,
        dataset_repo_id: str,
        episode: int = 0,
        robot_id: Optional[str] = None,
    ) -> subprocess.Popen:
        """
        Replay an episode from a dataset.
        Returns the subprocess so it can be monitored.
        """
        dataset_root = str(self._hf_cache / dataset_repo_id)

        cmd = [
            sys.executable,
            "-m", "lerobot.scripts.lerobot_replay",
            f"--robot.type={robot_type}",
            f"--robot.port={robot_port}",
            f"--dataset.repo_id={dataset_repo_id}",
            f"--dataset.root={dataset_root}",
            f"--dataset.episode={episode}",
        ]

        if robot_id:
            cmd.append(f"--robot.id={robot_id}")

        return self._run(cmd)

    def aggregate_datasets(
        self,
        dataset_repo_ids: list[str],
        output_repo_id: str,
    ) -> subprocess.Popen:
        """
        Aggregate multiple datasets into one.
        """
        # Import the aggregate function directly
        try:
            from lerobot.datasets.aggregate import aggregate_datasets as aggregate_func

            # Run in a separate thread/process to avoid blocking
            import threading

            def run_aggregate():
                aggregate_func(dataset_repo_ids, output_repo_id)

            thread = threading.Thread(target=run_aggregate)
            thread.start()

            # Return a mock process-like object
            class MockProcess:
                def __init__(self, thread):
                    self.thread = thread

                def poll(self):
                    return None if self.thread.is_alive() else 0

                def wait(self):
                    self.thread.join()
                    return 0

            return MockProcess(thread)

        except ImportError:
            raise RuntimeError("Could not import lerobot.datasets.aggregate")

    def teleoperate(
        self,
        robot_type: str,
        robot_port: str,
        teleop_type: str,
        teleop_port: str,
        robot_id: Optional[str] = None,
        teleop_id: Optional[str] = None,
        cameras_config: Optional[dict] = None,
        display_data: bool = False,
    ) -> subprocess.Popen:
        """Start teleoperation (leader controls follower, no recording)."""
        cmd = [
            sys.executable,
            "-m", "lerobot.scripts.lerobot_teleoperate",
            f"--robot.type={robot_type}",
            f"--robot.port={robot_port}",
            f"--teleop.type={teleop_type}",
            f"--teleop.port={teleop_port}",
        ]

        if robot_id:
            cmd.append(f"--robot.id={robot_id}")
        if teleop_id:
            cmd.append(f"--teleop.id={teleop_id}")

        if cameras_config:
            import json
            cameras_str = json.dumps(cameras_config)
            cmd.append(f"--robot.cameras={cameras_str}")

        if display_data:
            cmd.append("--display_data=true")

        return self._run(cmd)

    def train(
        self,
        dataset_repo_id: str,
        policy: str = "act",
        steps: int = 50000,
        batch_size: int = 8,
        save_freq: int = 10000,
        output_dir: Optional[str] = None,
    ) -> subprocess.Popen:
        """Train a policy on a dataset."""
        import time

        if not output_dir:
            name = dataset_repo_id.split("/")[-1]
            output_dir = f"outputs/train/{policy}_{name}_{time.strftime('%Y%m%d_%H%M%S')}"
        cmd = [
            sys.executable,
            "-m", "lerobot.scripts.lerobot_train",
            f"--dataset.repo_id={dataset_repo_id}",
            f"--policy.type={policy}",
            "--policy.push_to_hub=false",
            f"--steps={steps}",
            f"--batch_size={batch_size}",
            f"--save_freq={save_freq}",
            f"--output_dir={output_dir}",
        ]

        return self._run(cmd)

    def rollout(
        self,
        robot_type: str,
        robot_port: str,
        policy_path: str,
        task: str = "",
        duration_s: float = 30.0,
        robot_id: Optional[str] = None,
        cameras_config: Optional[dict] = None,
    ) -> subprocess.Popen:
        """Execute une politique entrainee (lerobot-rollout, strategie base : sans enregistrement)."""
        cmd = [
            sys.executable,
            "-m", "lerobot.scripts.lerobot_rollout",
            "--strategy.type=base",
            f"--policy.path={policy_path}",
            f"--robot.type={robot_type}",
            f"--robot.port={robot_port}",
            f"--duration={duration_s}",
        ]
        if robot_id:
            cmd.append(f"--robot.id={robot_id}")
        if task:
            cmd.append(f"--task={task}")
        if cameras_config:
            import json
            cmd.append(f"--robot.cameras={json.dumps(cameras_config)}")
        return self._run(cmd)

    def list_local_datasets(self) -> list[dict]:
        """List all local datasets."""
        try:
            cache_dir = Path.home() / ".cache" / "huggingface" / "lerobot"
            datasets = []
            if cache_dir.exists():
                for user_dir in cache_dir.iterdir():
                    if user_dir.is_dir() and user_dir.name not in ("calibration",):
                        for ds_dir in user_dir.iterdir():
                            if ds_dir.is_dir() and (ds_dir / "meta").exists():
                                repo_id = f"{user_dir.name}/{ds_dir.name}"
                                # Count episodes
                                data_dir = ds_dir / "data"
                                num_episodes = 0
                                if data_dir.exists():
                                    num_episodes = sum(
                                        1 for f in data_dir.rglob("*.parquet")
                                    )
                                datasets.append({
                                    "repo_id": repo_id,
                                    "path": str(ds_dir),
                                    "num_episodes": num_episodes,
                                })
            return datasets
        except Exception as e:
            print(f"Error listing datasets: {e}")
            return []

    def list_checkpoints(self) -> list[dict]:
        """List trained policies: every pretrained_model/ dir under outputs/ and trained/."""
        root = self.workdir
        checkpoints = []
        for base in (root / "outputs", root / "trained"):
            if base.exists():
                for cp in sorted(base.rglob("pretrained_model")):
                    if (cp / "config.json").exists():
                        checkpoints.append({
                            "name": str(cp.parent.relative_to(root)),
                            "path": str(cp),
                        })
        return checkpoints
