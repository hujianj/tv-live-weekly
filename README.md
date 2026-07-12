# TV Live Weekly

自动聚合公开 IPTV 源，每周完整检测真实可播放源，并生成酷9/TV 订阅列表。

## 推荐订阅地址

优先使用 GitHub Pages 地址，避免 jsDelivr 多节点缓存偶发返回旧版本：

```text
https://hujianj.github.io/tv-live-weekly/live-curated.txt
```

备用 jsDelivr 地址：

```text
https://cdn.jsdelivr.net/gh/hujianj/tv-live-weekly@main/live-curated.txt
```

M3U 格式：

```text
https://hujianj.github.io/tv-live-weekly/live.m3u
```

## 自动维护逻辑

- 每周一北京时间 04:20 自动运行完整源检测。
- 可在 GitHub Actions 手动点击 `Run workflow` 立即运行。
- 只发布通过真实 HLS/媒体分片验证的可播放源。
- 按当前电视观看习惯自动分类：央视、卫视、地方、影视剧场、少儿动漫、体育纪实、音乐综艺、生活休闲、综合娱乐、港澳台、海外华语。
- 自动 purge jsDelivr。
- 自动硬校验本地生成结果和 GitHub Raw 发布结果。
- 自动检查 GitHub Pages / jsDelivr 缓存状态；CDN 边缘缓存短时滞后只记录告警，不阻断主发布。

## 说明

jsDelivr 无版本路径可能出现旧缓存，因此不要使用不带 `@main` 的地址作为电视长期订阅地址。

不建议把 `gcore.jsdelivr.net @main` 设为电视长期订阅地址；它的边缘缓存刷新更不稳定。如需临时使用 CDN，优先使用上面的 `cdn.jsdelivr.net @main`，主订阅仍以 GitHub Pages 为准。

## 如何新增上游直播源

新增聚合源时，只需要修改这个文件：

```text
scripts/verify_sources.py
```

在文件顶部找到：

```python
SOURCES = [
    ("zbds_iptv4_txt", "https://live.zbds.top/tv/iptv4.txt"),
    ...
]
```

按同样格式新增一行即可：

```python
("your_source_name", "https://example.com/your_playlist.m3u"),
```

规则：

- `your_source_name` 建议只用英文、数字、下划线，不要用中文，避免日志里乱码。
- 第二个字段填写 TXT / M3U / M3U8 直播源地址。
- 添加后可以在 GitHub Actions 里手动点 `Run workflow`，或者等每周一自动维护。
- 如果想让某个新增源优先排序，可以继续修改同文件里的 `source_priority()` 函数。
- 当前最高优先级是 `zbds_iptv4_txt`，也就是：`https://live.zbds.top/tv/iptv4.txt`。
