# curl2video

Download a video you can already play in your browser by pasting the browser's **"Copy as cURL"**.

It's made for sites that send the video in small pieces (HLS, `.m3u8`) and only let it play inside their own page, because they check your session, cookies or some extra data on every request.

[Leer en español](README.es.md)

curl2video doesn't break or get around any protection. It reuses the request your browser already made (headers, cookies and links) and lets [yt-dlp](https://github.com/yt-dlp/yt-dlp) do the download. Videos protected with DRM are detected and skipped.

> Only download videos you have the right to keep, and respect each site's terms and the work of the people who make the videos.

## What it does for you

- Checks the playlist and the first piece before starting, and tells you clearly if something is wrong.
- Uses your browser's session for every piece.
- If the download gets cut, run it again with the same name and it continues where it stopped.
- When it finishes, it compares the file's length with the playlist to confirm it's complete.
- Speaks English and Spanish.

## What you need

- Python 3.8 or newer
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (a recent version)
- [ffmpeg](https://ffmpeg.org)

## Installation

### Linux (Debian, Ubuntu, Linux Mint)

1. Install the tools:
   ```
   sudo apt install python3 ffmpeg pipx
   pipx install yt-dlp
   pipx ensurepath
   ```
   Close the terminal and open it again.
2. Download `curl2video.py` from this page (open the file and click "Download raw file").
3. Open a terminal in the folder where you saved it and run:
   ```
   install -Dm755 curl2video.py ~/.local/bin/curl2video
   ```
   From now on you start it by typing `curl2video`.

On Arch Linux, step 1 is `sudo pacman -S python ffmpeg yt-dlp`.

### macOS

1. Install [Homebrew](https://brew.sh) if you don't have it, then run:
   ```
   brew install python yt-dlp ffmpeg
   ```
2. Download `curl2video.py`, open a terminal in that folder and start it with:
   ```
   python3 curl2video.py
   ```

### Windows

1. Open PowerShell and run these three lines:
   ```
   winget install Python.Python.3.13
   winget install yt-dlp.yt-dlp
   winget install Gyan.FFmpeg
   ```
   Close PowerShell and open it again.
2. Download `curl2video.py`, go to that folder in PowerShell (for example `cd Downloads`) and start it with:
   ```
   python curl2video.py
   ```

## How to use it

1. Open the video page in your browser (Chrome, Edge, Brave or Firefox).
2. Press **F12** and go to the **Network** tab.
3. Type `m3u8` in the filter box and play the video. If nothing shows up, reload the page (F5) and play it again.
4. Right-click the request that ends in `.m3u8` → **Copy** → **Copy as cURL**.
   On Windows, choose the **(bash)** or **(POSIX)** option.
5. Start curl2video, paste what you copied and press Enter.
   In a Linux terminal you paste with Ctrl+Shift+V. The terminal may ask you to confirm because the text has several lines: that's normal.
6. If it says **the pieces need their own permission**, copy the request of one piece in the same way (it usually ends in `.ts`, `.m4s`, `.aac` or `.mp4`) and paste it too.
7. Type a name for the file, or press Enter to use the one it suggests.
8. Wait until it says **Done**. The video is saved in the folder the terminal is in.

Tip: pause the video in the browser while it downloads, so it doesn't compete for your connection.

## Language

curl2video uses your system's language (English or Spanish). To change it (your choice is remembered):

```
curl2video --lang en
curl2video --lang es
```

On macOS and Windows, write `python3 curl2video.py --lang en` or `python curl2video.py --lang en`.

## Settings

The settings live in `~/.config/curl2video.conf` (on Windows, `C:\Users\YOUR_USER\.config\curl2video.conf`):

```
LANG=en
N=3
```

`N` is how many pieces it downloads at the same time. Higher can be faster, but many sites start refusing requests (error 429) above 3 or 4.

## If something goes wrong

| What you see | What to do |
| --- | --- |
| `Checking the playlist: 403` (or 401, 404, 410) | The request expired or belongs to another session. Reload the page, play the video and copy the request again. If you use a VPN or proxy only in the browser, turn it off or use it for the whole computer. |
| `429` | The site says there are too many requests. Pause the video in the browser, wait a minute and try again. If it happens a lot, lower `N` in the settings. |
| It stopped halfway | Run it again with a freshly copied request of the same video and the same name: it continues where it stopped. |
| `This video is protected with DRM` | It can't be downloaded. curl2video doesn't get around DRM. |
| `Live HLS streams are not supported...` or `Sleeping ... seconds` | Normal. You can ignore them. |
| `yt-dlp is not installed` | Install it (see Installation). If it's installed, close the terminal and open it again. |

If yt-dlp shows a strange error, update it: `pipx upgrade yt-dlp` (Linux), `brew upgrade yt-dlp` (macOS) or `winget upgrade yt-dlp.yt-dlp` (Windows).

## Privacy

What you copy with "Copy as cURL" can include your cookies, which work like a temporary password to your account. Don't share it with anyone and don't paste it in public places, such as an issue on this page. curl2video only sends it to the video's own server and keeps the cookies in a temporary file that it deletes when the download ends.

## How it works

1. It reads the address and the headers (user-agent, origin, cookies...) of the request you pasted.
2. It opens the playlist with those same headers, counts the pieces and tests the first one.
3. If the pieces need extra data in their address, it takes it from the piece request you paste and adds it to every piece.
4. It passes everything to yt-dlp, which downloads and joins the pieces, and at the end it checks the length with ffprobe.
