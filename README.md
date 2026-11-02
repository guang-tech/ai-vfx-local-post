# ai-vfx-local-post

用于拆卡、拆包、产品亮相等动效的 Codex skill：将视觉设定、AI纯光效生成、原资产本地合成和Alpha/RGB交付串成可追溯流程。入口是 [SKILL.md](SKILL.md)。

仓库维护通用流程、参考规范、项目记录模板和本地检查工具。它不是一键渲染器，不包含主题素材、生成视频、平台凭据或付费授权。平台操作使用项目中已配置的工具与当前授权。

## 使用与安装

将本仓库克隆到工作目录进行维护。安装到Codex时，将 `SKILL.md`、`agents/`、`assets/`、`references/`、`scripts/` 放入 `$CODEX_HOME/skills/ai-vfx-local-post`（未设置CODEX_HOME时为用户目录下的 `.codex/skills/ai-vfx-local-post`）。已有安装先比对本地改动，不直接删除重建。仓库管理文件与tests无需复制进安装目录。

在对话中使用 `$ai-vfx-local-post`，或由相关视觉后期任务自动选用。保留默认自动发现策略。每个新主题有独立工程目录；生成规格逐批确认，原图、源片与实际验收状态以该主题记录为准。

## 本地工具

需要Python 3.10+；媒体检查额外需要显式指定FFmpeg。工具无网络调用，不执行付费生成。

|工具|用途|
|---|---|
|`scripts/fx_media.py`|媒体全解码、帧数/PTS/尺寸检查、联系表及兼容导出|
|`scripts/fx_manifest.py`|显式依赖清单的SHA256快照与复核|
|`scripts/fx_geometry.py`|已测量光框与原卡四边误差审核；不自动识别画面|

先运行各工具的 `--help`。生成文件不覆盖既有报告或输出。项目状态模板见 [production.example.json](assets/production.example.json)，模板中的null须按项目实际填写，历史项目不自动迁移。

## 本次经验更新（2026-11-02）

- 卡框验收从中心扩展到四边、四角和分阶段实测；配置公式自洽不算像素证据。
- 生成前拆分多联设定、复核网页载入后的参考顺序；生成后记录实际尺寸、fps和帧数。
- 保留真实封条分离、刚体盒形、原图清晰度；区分白色Alpha剪影与预乘RGB。
- 局部修订核对取帧/变换/原图像素与未改视频哈希；待审案例不升级为通过。

近期卡框修订案例仍处于待用户审看状态，本次只沉淀已定位的问题与验证边界。公开版本使用匿名案例及通用路径，项目私有记录留在项目本地。

## 验证与维护

```powershell
python -B -m unittest discover -s tests -v
python -B scripts/fx_geometry.py --help
python -B scripts/fx_media.py --help
python -B scripts/fx_manifest.py --help
```

可用时运行Codex `skill-creator/scripts/quick_validate.py`，并检查本地Markdown链接和JSON解析。技术脚本通过不代表动效内容、正常速度播放或客户端混合通过；各状态分别记录。
