<p align="center">
  <img src="imgs/card_crop.png" width="50%"/>
  <br>
</p>

[![GitHub release](https://img.shields.io/github/release/KurtBestor/Hitomi-Downloader.svg?logo=github)](https://github.com/KurtBestor/Hitomi-Downloader/releases/latest)
[![GitHub downloads](https://img.shields.io/github/downloads/KurtBestor/Hitomi-Downloader/latest/total.svg?logo=github)](https://github.com/KurtBestor/Hitomi-Downloader/releases/latest)
[![GitHub downloads](https://img.shields.io/github/downloads/KurtBestor/Hitomi-Downloader/total.svg?logo=github)](https://github.com/KurtBestor/Hitomi-Downloader/releases)

## Links
- [Download](https://github.com/KurtBestor/Hitomi-Downloader/releases/latest)
- [Issues](https://github.com/KurtBestor/Hitomi-Downloader/issues)
- [Scripts & Plugins](https://github.com/KurtBestor/Hitomi-Downloader/wiki/Scripts-&-Plugins)
- [Chrome Extension](https://github.com/KurtBestor/Hitomi-Downloader/wiki/Chrome-Extension)

## Demo
<img src="imgs/how_to_download.gif">

## Features
- 🍰 Simple and clear user interface
- 🚀 Download acceleration
- 💻 Supports 24 threads in a single task
- 🚥 Supports speed limit
- 📜 Supports user scripts
- 🧲 Supports BitTorrent & Magnet
- 🎞️ Supports M3U8 & MPD format videos
- 🌙 Dark mode
- 🧳 Portable
- 📋 Clipboard monitor
- 🗃️ Easy to organize tasks

## Supported Sites
| Site | URL |
| :--: | -- |
| **4chan** | <https://4chan.org> |
| **AfreecaTV** | <https://afreecatv.com> |
| **ArtStation** | <https://artstation.com> |
| **baraag.net** | <https://baraag.net> |
| **bilibili** | <https://bilibili.com> |
| **ComicWalker** | <https://comic-walker.com> |
| **Coub** | <https://coub.com> |
| **DeviantArt** | <https://deviantart.com> |
| **Facebook** | <https://facebook.com> |
| **FC2 Video** | <https://video.fc2.com> |
| **Flickr** | <https://flickr.com> |
| **Hameln** | <https://syosetu.org> |
| **Imgur** | <https://imgur.com> |
| **Instagram** | <https://instagram.com> |
| **カクヨム** | <https://kakuyomu.jp> |
| **Mastodon** | <https://mastodon.social> |
| **Misskey** | <https://misskey.io> |
| **Naver Blog** | <https://blog.naver.com> |
| **Naver Cafe** | <https://cafe.naver.com> |
| **Naver Post** | <https://post.naver.com> |
| **Naver Webtoon** | <https://comic.naver.com> |
| **Naver TV** | <https://tv.naver.com> |
| **Niconico** | <http://nicovideo.jp> |
| **Pawoo** | <https://pawoo.net> |
| **Pinterest** | <https://pinterest.com> |
| **Pixiv** | <https://pixiv.net> |
| **pixivコミック** | <https://comic.pixiv.net> |
| **Soundcloud** | <https://soundcloud.com> |
| **小説家になろう** | <https://syosetu.com> |
| **TikTok** | <https://tiktok.com><br><https://douyin.com>|
| **Tumblr** | <https://tumblr.com> |
| **Twitch** | <https://twitch.tv> |
| **Twitter** | <https://twitter.com> |
| **Vimeo** | <https://vimeo.com> |
| **Wayback Machine** | <https://archive.org> |
| **Weibo** | <https://weibo.com> |
| **WikiArt** | <https://www.wikiart.org> |
| **Youku** | <https://youku.com> |
| **YouTube** | <https://youtube.com> |
| **and more...** | [Supported sites by yt-dlp](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) |

## Local Patch Workflow

This repo also contains a local reverse-engineering workflow for fixing bugs in the packaged
`hitomi_downloader_GUI.exe` when the public source tree does not match the released binary.

Current local artifacts:

- Original binary: `hitomi_downloader_GUI.exe`
- Extracted archive notes: `_archive_recursive.txt`, `_archive_view.txt`
- Extracted bytecode and decompiled modules: `_extracted/`
- Patched binary output: `_patched/hitomi_downloader_GUI_patched.exe`
- Patch script: `tools/patch_twitter_url_fix.py`

The current patch fixes:

1. A Twitter/X URL normalization bug that caused errors like:
   `Invalid: [twitter] https://x.com/<username>`
   - module: `extractor.twitter_downloader`
   - function: `Downloader_twitter.fix_url`
   - effect: preserves full `https://x.com/...` and `https://twitter.com/...` profile URLs instead of collapsing them during normalization

2. Startup update popup annoyance:
   - module: entrypoint `hitomi_downloader_GUI`
   - function: `update`
   - effect: replaces the modal message box prompt with a no-op while keeping background rule/script synchronization intact

3. Instagram user profile URL parsing bug that caused errors like:
   `Invalid: [insta] https://www.instagram.com/<username>`
   - module: `extractor.insta_downloader`
   - function: `API.get_user_info`
   - effect: safely extracts the username directly from the profile URL instead of relying on Instagram's discontinued `<meta property="og:url">` tag, preventing `TypeError` on `NoneType`

4. Weibo user profile & album download error:
   `Invalid: [weibo] https://weibo.com/u/<uid>`
   - module: `extractor.weibo_downloader`
   - function: `get_id`, `get_imgs`, `ensure_cookies`, `read_json_api`
   - effect: replaces outdated HTML page scraping and `clf2.solve` with Weibo's modern visitor ticket API and REST AJAX APIs (`/ajax/profile/info` and `/ajax/profile/getImageWall`), resolving timeout crashes (`Invalid: [weibo]`) and 403 authorization blocks.

Quick reuse checklist for future binary-only fixes:

1. Keep the target `hitomi_downloader_GUI.exe` in the repo root.
2. Extract or inspect modules from `PYZ-00.pyz`.
3. Patch the smallest possible function instead of recompiling the whole decompiled module.
4. Rebuild a patched `PYZ`, then rebuild a patched exe into `_patched/`.
5. Validate the patched function behavior before testing the GUI.

Why patch only a function:

- Decompiled source may be incomplete or syntactically broken.
- Replacing a single code object is usually safer than rebuilding a whole module from noisy decompilation output.
- It makes future bug patches easier to isolate and review.

If another packaged-only bug shows up later, start by checking whether it lives in:

- `extractor.*` for site-specific URL and media parsing bugs
- `utils`, `downloader`, or `tasks` for shared download logic
- `translator` or frontend-related modules only if the failure is clearly UI-side
