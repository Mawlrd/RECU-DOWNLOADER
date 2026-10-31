# curl2video

Baja un video que ya puedes ver en tu navegador, pegando el **"Copy as cURL"** del navegador.

Está pensado para sitios que mandan el video en pedacitos (HLS, `.m3u8`) y solo lo dejan ver dentro de su propia página, porque en cada pedido revisan tu sesión, tus cookies o algún dato extra.

[Read in English](README.md)

curl2video no rompe ni saltea ninguna protección. Reusa el pedido que tu navegador ya hizo (cabeceras, cookies y links) y deja que [yt-dlp](https://github.com/yt-dlp/yt-dlp) haga la descarga. Los videos con DRM se detectan y no se bajan.

> Baja solo videos que tengas derecho a guardar, y respeta las reglas de cada sitio y el trabajo de quienes hacen los videos.

## Qué hace por ti

- Revisa la lista y el primer pedacito antes de empezar, y te dice claro si algo anda mal.
- Usa la sesión de tu navegador para cada pedacito.
- Si la descarga se corta, la ejecutas de nuevo con el mismo nombre y sigue desde donde quedó.
- Al terminar, compara la duración del archivo con la de la lista para confirmar que está completo.
- Habla español e inglés.

## Qué necesitas

- Python 3.8 o más nuevo
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (una versión reciente)
- [ffmpeg](https://ffmpeg.org)

## Instalación

### Linux (Debian, Ubuntu, Linux Mint)

1. Instala las herramientas:
   ```
   sudo apt install python3 ffmpeg pipx
   pipx install yt-dlp
   pipx ensurepath
   ```
   Cierra la terminal y vuelve a abrirla.
2. Descarga `curl2video.py` desde esta página (abre el archivo y haz clic en "Download raw file").
3. Abre una terminal en la carpeta donde lo guardaste y ejecuta:
   ```
   install -Dm755 curl2video.py ~/.local/bin/curl2video
   ```
   Desde ahora lo inicias escribiendo `curl2video`.

En Arch Linux, el paso 1 es `sudo pacman -S python ffmpeg yt-dlp`.

### macOS

1. Instala [Homebrew](https://brew.sh) si no lo tienes, y después ejecuta:
   ```
   brew install python yt-dlp ffmpeg
   ```
2. Descarga `curl2video.py`, abre una terminal en esa carpeta e inícialo con:
   ```
   python3 curl2video.py
   ```

### Windows

1. Abre PowerShell y ejecuta estas tres líneas:
   ```
   winget install Python.Python.3.13
   winget install yt-dlp.yt-dlp
   winget install Gyan.FFmpeg
   ```
   Cierra PowerShell y vuelve a abrirlo.
2. Descarga `curl2video.py`, ve a esa carpeta en PowerShell (por ejemplo `cd Downloads`) e inícialo con:
   ```
   python curl2video.py
   ```

## Cómo usarlo

1. Abre la página del video en el navegador (Chrome, Edge, Brave o Firefox).
2. Presiona **F12** y ve a la pestaña **Network** (Red).
3. Escribe `m3u8` en el filtro y reproduce el video. Si no aparece nada, recarga la página (F5) y vuelve a reproducirlo.
4. Clic derecho sobre el pedido que termina en `.m3u8` → **Copy** → **Copy as cURL**.
   En Windows, elige la opción **(bash)** o **(POSIX)**.
5. Inicia curl2video, pega lo que copiaste y presiona Enter.
   En la terminal de Linux se pega con Ctrl+Shift+V. La terminal puede pedirte que confirmes porque el texto tiene varias líneas: es normal.
6. Si dice que **los pedacitos necesitan su propio permiso**, copia de la misma forma el pedido de un pedacito (suele terminar en `.ts`, `.m4s`, `.aac` o `.mp4`) y pégalo también.
7. Escribe un nombre para el archivo, o presiona Enter para usar el que te sugiere.
8. Espera a que diga **Listo**. El video queda en la carpeta donde está la terminal.

Consejo: pausa el video en el navegador mientras se baja, así no compite por tu conexión.

## Idioma

curl2video usa el idioma de tu sistema (español o inglés). Para cambiarlo (queda guardado):

```
curl2video --lang es
curl2video --lang en
```

En macOS y Windows se escribe `python3 curl2video.py --lang es` o `python curl2video.py --lang es`.

## Configuración

La configuración está en `~/.config/curl2video.conf` (en Windows, `C:\Users\TU_USUARIO\.config\curl2video.conf`):

```
LANG=es
N=3
```

`N` es cuántos pedacitos baja a la vez. Con más puede ir más rápido, pero muchos sitios empiezan a rechazar pedidos (error 429) por encima de 3 o 4.

## Si algo falla

| Lo que ves | Qué hacer |
| --- | --- |
| `Revisando la lista: 403` (o 401, 404, 410) | El pedido venció o es de otra sesión. Recarga la página, reproduce el video y copia el pedido de nuevo. Si usas una VPN o proxy solo en el navegador, apágala o úsala en toda la computadora. |
| `429` | El sitio dice que hay demasiados pedidos. Pausa el video en el navegador, espera un minuto y prueba de nuevo. Si pasa seguido, baja `N` en la configuración. |
| Se cortó a la mitad | Ejecútalo de nuevo con un pedido recién copiado del mismo video y el mismo nombre: sigue desde donde quedó. |
| `Este video tiene DRM` | No se puede bajar. curl2video no saltea el DRM. |
| `Live HLS streams are not supported...` o `Sleeping ... seconds` | Es normal. Puedes ignorarlos. |
| `No encuentro yt-dlp` | Instálalo (mira Instalación). Si ya está instalado, cierra la terminal y vuelve a abrirla. |

Si yt-dlp muestra un error raro, actualízalo: `pipx upgrade yt-dlp` (Linux), `brew upgrade yt-dlp` (macOS) o `winget upgrade yt-dlp.yt-dlp` (Windows).

## Privacidad

Lo que copias con "Copy as cURL" puede incluir tus cookies, que funcionan como una contraseña temporal de tu cuenta. No se lo pases a nadie ni lo pegues en lugares públicos, como un issue de esta página. curl2video solo se lo manda al servidor del propio video, y guarda las cookies en un archivo temporal que borra al terminar la descarga.

## Cómo funciona

1. Lee la dirección y las cabeceras (user-agent, origin, cookies...) del pedido que pegaste.
2. Abre la lista con esas mismas cabeceras, cuenta los pedacitos y prueba el primero.
3. Si los pedacitos necesitan datos extra en su dirección, los toma del pedido de pedacito que pegues y se los agrega a cada uno.
4. Le pasa todo a yt-dlp, que baja y une los pedacitos, y al final revisa la duración con ffprobe.
