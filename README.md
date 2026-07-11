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

备用 gcore 地址：

```text
https://gcore.jsdelivr.net/gh/hujianj/tv-live-weekly@main/live-curated.txt
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
- 自动 purge jsDelivr，并对 CDN `@main` 地址做新鲜度校验。

## 说明

jsDelivr 无版本路径可能出现旧缓存，因此不要使用不带 `@main` 的地址作为电视长期订阅地址。
