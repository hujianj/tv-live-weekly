# TV Live Weekly

自动聚合公开 IPTV 源，每周完整检测真实可播放源，并生成酷9/TV 订阅列表。

## 订阅地址

仓库创建后，优先使用 jsDelivr：

```text
https://cdn.jsdelivr.net/gh/hujianj/tv-live-weekly@main/live-curated.txt
```

备用：

```text
https://gcore.jsdelivr.net/gh/hujianj/tv-live-weekly@main/live-curated.txt
```

## 自动维护逻辑

- 每周一北京时间 04:20 自动运行完整源检测。
- 可在 GitHub Actions 手动点击 `Run workflow` 立即运行。
- 只发布通过真实 HLS/媒体分片验证的可播放源。
- 按当前电视观看习惯自动分类：央视、卫视、地方、影视剧场、少儿动漫、体育纪实、音乐综艺、生活休闲、综合娱乐、港澳台、海外华语。

> 注意：长期订阅地址使用 @main，避免 jsDelivr 无版本路径出现旧缓存。

