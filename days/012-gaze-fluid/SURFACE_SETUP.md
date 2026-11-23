# Day 12 — 实时屏幕定位与眼睛叠加

这套扩展从 Neon 的场景视频识别四个 AprilTag，把注视点映射到 TouchDesigner 作品画面。眼睛视频另行检测两个画面区域中的瞳孔候选位置与画面变化区域。Neon 提供的左右瞳孔直径仍是独立的眼状态数值。图像框选只是视觉估计，不应视为生理测量。

## 旧版 AprilTag 实验

Day 12 音效版默认使用 Neon 场景摄像机坐标，画面不显示定位标记。这里记录早期带眼睛小窗的屏幕校准实验；其中的本地恢复工程未随仓库发布。

1. 在 TouchDesigner 打开已验证可运行的 `Day12-Recovery-Eye-Inset.toe`。保持当前工程，**不要打开** `.toe.unstable` 文件。
2. 打开 **Dialogs → Textport and DATs**，粘贴下面这一行。它只修改内存中的工程，不会自动覆盖 `.toe`：

   ```python
   DAY12 = "/absolute/path/to/days/012-gaze-fluid"; exec(compile(open(DAY12 + "/install_surface_eye_overlay.py", encoding="utf-8").read(), "install_surface_eye_overlay.py", "exec"))
   ```

3. 打开 `/project1/day12_gaze_fluid/VISUAL_RENDER/out_picture`。作品四角应该出现四个不同的黑白 AprilTag，右上角是眼摄像头。把这个输出放在需要交互的显示器上，尽量占据屏幕大部分面积；让 Neon **场景摄像头**看清所有标记。标记不能被眼睛小窗、鼠标或窗口边框遮住。
4. 停止之前的 Day 12 桥接程序或 TD-Neon，保证只有一个程序发送到本机 UDP 9012。安装依赖：

   ```sh
   .venv/bin/python -m pip install -r requirements-mapping.txt
   ```

5. 在本目录启动实时映射。用你自己的 Companion 地址替换 `COMPANION_IP`：

   ```sh
   .venv/bin/python neon_bridge.py --port 9012 live --device COMPANION_IP --surface-layout media/surface-layout.json --eye-features
   ```

6. 终端应该从 `AprilTags 0/4 | surface lost` 变成至少 `AprilTags 3/4 | surface visible`。TouchDesigner 的 `GAZE_FEATURES/debug` 应显示 `receiving | valid 1`。视线离开画面或不足三个标记被识别时会显示 `valid 0`，作品停止注入新力量，原有流体仍继续运动。确认稳定后，通过 TouchDesigner 的 **File → Save As** 另存一个新的 `.toe`。

## 输出与调节

- `media/surface-markers.png` 是 1200×815 的标记参考图；最终画面的 shader 直接绘制相同的四个 AprilTag，避免图片透明通道在 TouchDesigner 中没有显示。`media/surface-layout.json` 记录四个标签的角点坐标，绘制尺寸与布局必须保持一致。
- Python 桥接继续输出原有 `/gx /gy /valid`，但开启 `--surface-layout` 后它们表示**作品平面坐标**。`/raw_gx /raw_gy` 仍保留场景摄像头归一化坐标。
- `/eye_l_*`、`/eye_r_*` 是眼视频左右半幅中检测的瞳孔中心、视频半径和可信度；小窗内圈框跟随它们。`/pupil_l /pupil_r` 是 Neon 的毫米数值，分别显示在两个区域下方。三组 `/eye_changeN_*` 表示相邻眼视频帧之间最明显的像素变化，青色框及旁边的两位数字是图像变化强度百分比。眼睛到背景注视端点的连线跟随有效注视。
- 如果画面倒置或左右标注与真实眼别不一致，应先检查眼摄像头的实际输出方向；当前代码把“画面左半/右半”作为检测区域，并不假设它们对应解剖学左右眼。
- 如果标记太小，可用 `make_surface_markers.py --width W --height H --output media` 重新生成标记和布局；同时把 TouchDesigner 输出宽高设为同样的 `W×H`，重新执行安装脚本。
- Neon 当前 API 的相机标定端点返回 404，所以此版采用 AprilTag 平面单应性映射。它能修正屏幕透视和头部移动，但镜头畸变及视频/注视时间差仍可能造成残差。映射没有成功时不会偷偷退回不准确的场景坐标。

## 验证范围

在 Apple M4 Pro 上已验证：Neon 场景视频 1600×1200、眼视频 384×192 可读取；真实眼视频帧中的两个瞳孔候选被检测；合成的四标签画面检测到 4/4，透视回算中心误差约 0.2 像素；遮挡两个标签或场景帧过期会使映射失效；新 GLSL 在本机 OpenGL 编译通过。TouchDesigner 中运行安装脚本和实拍屏幕标签后的准确度还需现场验证。不要把 `.toe.unstable` 当作已验证工程。
