# Weekend Colony Watch — Remote time-lapse observation of culture dishes in an anaerobic chamber

English | [日本語](README.ja.md)

Final project for the Physical AI Applied Course 1: "Creative tasks with AI × robotics".
In ROS 2 + Gazebo, a UR3e arm checks a culture dish every six hours through the closed lid.
Time-lapse tracking of the fixed-camera images detects colony emergence, notifies the
researcher, and opens the lid only when a colony is confirmed: the arm lifts the lid by
suction, takes a record photo, and puts the lid back right away.

- Video (YouTube, 2 min 57 s, real time and 5× speed; playback speed is shown at the top left at all times): https://youtu.be/d6FZ36axxk0
- Report (PDF): submitted via omnicampus
- This repository: all code and evaluation results (image data and recordings are not included)

## The problem

Anaerobic bacteria take one to three days to form visible colonies after inoculation, so a
dish inoculated on Friday is not seen again until Monday. Looking through the lid is error-prone
because ceiling lights reflect off the polystyrene, yet the chamber is oxygen-free but not
sterile, so the lid should be opened as little as possible. "Open the lid to see clearly"
and "keep the lid closed" pull in opposite directions.

The system resolves this with two ideas.

1. **Time-lapse tracking.** With a fixed camera and a fixed dish position, candidates are detected from the difference against the t=0 image, tracked over time, and separated into colonies (which grow) and artifacts such as reflections and dust (which do not).
2. **Adaptive opening (policy 6).** A suspected colony is reported without opening the lid; the lid is opened only once a colony is confirmed, to take a photo for the notification. Two openings in 72 hours (about 18 s in total).

## Main results (synthetic images, held-out seeds 100–129, 557 ground-truth colonies)

| Condition | Detected | Missed | False positives | Detection delay (median) |
|---|---|---|---|---|
| Lid off | 554 | 3 | 0 | 11.5 h |
| Through lid | 553 | 4 | 0 | 11.7 h |
| Simulated polarizer | 556 | 1 | 0 | 11.4 h |

Opening policies (through lid, per dish over 72 h): open every time 13.0 openings / 116 s →
policy 6 2.0 openings / 18 s. From the first colony's appearance, the "suspected" notice
arrives after a median of 5.1 h and the "confirmed" notice after 11.1 h. Zero false alarms
on 30 empty dishes. See `results/` and the report for details.

## Repository layout

| Path | Contents |
|---|---|
| `docker/` | Container setup for the ROS 2 Jazzy + Gazebo Harmonic environment |
| `ros2_ws/src/dish_description/` | Models of the dish, lid, rack and fixed camera, and the world file |
| `ros2_ws/src/dish_bringup/scripts/lid_cycle.py` | Lid handling (four poses HIGH / DOWN / LIFT / RETRACT; suction simulated with DetachableJoint) |
| `ros2_ws/src/dish_bringup/scripts/patrol.py` | Patrol that opens the lid every time (P0, for comparison) |
| `ros2_ws/src/dish_bringup/scripts/patrol6.py` | Adopted patrol (policy 6: notify on suspicion, open on confirmation) |
| `ros2_ws/src/dish_bringup/scripts/run_patrol.sh` | Runs each observation time in its own process with timeouts, recovery and retries |
| `ros2_ws/src/dish_bringup/scripts/recover.py` | Recovery after a hang (release suction, return to the rest pose) |
| `ros2_ws/src/dish_bringup/scripts/dish_vision.py` | Top-down rectification of the camera image and the call into the detector |
| `ros2_ws/src/dish_bringup/scripts/detect_track.py` | Detector (identical to the copy in `tools/eval`) |
| `ros2_ws/src/dish_bringup/scripts/save_image.py` | Saves camera frames |
| `scripts/` | Helper scripts |
| `tools/synth/` | Synthetic dish image generator (growth model, reflections, dust, bubbles, ground-truth labels). Managed with uv |
| `tools/eval/` | Detection and tracking (`detect_track.py`), diagnostics, opening-policy comparison, empty-dish evaluation. Managed with uv |
| `tools/gz/` | Retract-pose computation (UR3e DH parameters, projection into the camera view) |
| `tools/video/` | Video panel generation, compositing, and intrusion scans of the screen recording |
| `tools/tts/` | Narration generation (Kokoro, local text-to-speech) |
| `results/` | Evaluation outputs and patrol logs (`heldout_100_129.txt`, `policy_sim_lid_100_129.txt`, ...) |

`data/` (synthetic images) and `recordings/` (screen recordings and the video) are excluded by `.gitignore`.
ROS 2 nodes are built with colcon; `tools/*` use uv, so the Python environments stay separate.

## How to run (overview)

Environment: Ubuntu 24.04 (arm64), Docker, NVIDIA GPU. ROS 2 Jazzy and Gazebo Harmonic run
inside the container; synthesis, evaluation and video tools run in their own uv environments under `tools/*`.

**1. Generate synthetic images (host)**

~~~
cd tools/synth && uv sync && uv run python synth.py --seed 112
~~~

**2. Evaluate detection and tracking (host)**

~~~
cd tools/eval && uv sync && uv run python detect_track.py
~~~

**3. Start Gazebo (inside the container)**

~~~
ros2 launch ur_simulation_gz ur_sim_control.launch.py
~~~

**4. Spawn the dish (inside the container)**

~~~
~/ros2_ws/src/dish_bringup/scripts/spawn_dish.sh
~~~

**5. Run the patrol (from the host, in the background)**

~~~
docker exec -d pai-sim bash -c 'PATROL=patrol6.py ~/ros2_ws/src/dish_bringup/scripts/run_patrol.sh 0 6 12 18 24 30 36 42 48 54 60 66 72 > ~/recordings/patrol6_run.log 2>&1'
~~~

Arguments and settings are documented in the header comments of each script and in `CFG` of `tools/eval/detect_track.py`.

## What is simulated, and limitations

- Suction is simulated with Gazebo's DetachableJoint; no physical suction force is modeled.
- The polarizer is simulated by attenuating reflections to 0.25×.
- The dish contents are synthetic images shown on an emissive plane placed above the lid. They are unaffected by scene lighting, and the reflections are drawn into the synthetic images.
- Reflections and dust in the synthetic images do not move between observations, so the effect of the time difference and the zero false alarms on empty dishes may be optimistic compared with a real setup.
- Held-out seeds come from the same generator as the tuning seeds; generalization to real images is untested.
- Notifications are only written to a log file (`notify_log.jsonl`); no delivery channel is implemented.
- Collision meshes for the UR3e could not be generated, so collisions were checked only by computation.

## Tools used

ROS 2 Jazzy, Gazebo Harmonic (ros_gz), Universal Robots ROS 2 Gazebo Simulation (UR3e),
MoveIt2, Python / OpenCV / NumPy, uv, Docker, ffmpeg, Kokoro (text-to-speech).
The course materials (ROS 2 + Gazebo integration, UR3 pick-and-place) were used as references
for the launch setup; the task design, detector, patrol and evaluation are original work.

## License

MIT License
