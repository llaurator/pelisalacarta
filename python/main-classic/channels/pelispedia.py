# -*- coding: utf-8 -*-
# ------------------------------------------------------------
# pelisalacarta - XBMC Plugin
# http://blog.tvalacarta.info/plugin-xbmc/pelisalacarta/
# ------------------------------------------------------------

import re
import time
import urllib
import urllib2
import urlparse

from core import config
from core import logger
from core import scrapertools
from core import servertools
from core.item import Item

__channel__ = "pelispedia"
__category__ = "F,S,VOS"
__type__ = "generic"
__title__ = "PelisPedia"
__language__ = "ES"

CHANNEL_HOST = "http://pelispedia.tv/"
DEBUG = config.get_setting("debug")
fanart_host = "http://i.imgur.com/9QbyJrf.jpg"

CHANNEL_DEFAULT_HEADERS = [
    ["User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:22.0) Gecko/20100101 Firefox/22.0"],
    ["Accept-Encoding", "gzip, deflate"],
    ["Referer", CHANNEL_HOST]
]


def isGeneric():
    return True


def mainlist(item):
    logger.info("pelisalacarta.channels.pelispedia mainlist")

    itemlist = list()
    itemlist.append(Item(channel=__channel__, action="listado", title="[B]Películas[/B]",
                         url=urlparse.urljoin(CHANNEL_HOST, "movies/all/"), fanart=fanart_host, extra="movies"))
    itemlist.append(Item(channel=__channel__, action="listado_alfabetico", title="     Por orden alfabético",
                         url=urlparse.urljoin(CHANNEL_HOST, "movies/all/"), extra="movies", fanart=fanart_host))
    itemlist.append(Item(channel=__channel__, action="listado_genero", title="     Por género",
                         url=urlparse.urljoin(CHANNEL_HOST, "movies/all/"), extra="movies", fanart=fanart_host))
    itemlist.append(Item(channel=__channel__, action="listado_anio", title="     Por año",
                         url=urlparse.urljoin(CHANNEL_HOST, "movies/all/"), extra="movies", fanart=fanart_host))
    itemlist.append(Item(channel=__channel__, action="search", title="     Buscar...",
                         url=urlparse.urljoin(CHANNEL_HOST, "buscar/?s="), extra="movies", fanart=fanart_host))
    itemlist.append(Item(channel=__channel__, action="listado", title="[B]Series[/B]",
                         url=urlparse.urljoin(CHANNEL_HOST, "series/all/"), extra="serie", fanart=fanart_host))
    itemlist.append(Item(channel=__channel__, action="listado_alfabetico", title="     Por orden alfabético",
                         extra="serie", fanart=fanart_host))
    itemlist.append(Item(channel=__channel__, action="listado_genero", title="     Por género", extra="serie",
                         fanart=fanart_host))
    itemlist.append(Item(channel=__channel__, action="listado_anio", title="     Por año", extra="serie",
                         fanart=fanart_host))
    itemlist.append(Item(channel=__channel__, action="search", title="     Buscar...",
                         url=urlparse.urljoin(CHANNEL_HOST, "series/buscar/?s="), extra="serie", fanart=fanart_host))

    return itemlist


def listado_alfabetico(item):
    logger.info("pelisalacarta.channels.pelispedia listado_alfabetico")

    itemlist = []

    for letra in ['0-9', 'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S',
                  'T', 'U', 'V', 'W', 'X', 'Y', 'Z']:

        cadena = "series/letra/"
        if item.extra == "movies":
            cadena = 'movies/all/?letra='
            if letra == '0-9':
                cadena += "Num"
            else:
                cadena += letra
        else:
            if letra == '0-9':
                cadena += "num/"
            else:
                cadena += letra+"/"

        itemlist.append(Item(channel=__channel__, action="listado", title=letra, url=urlparse.urljoin(CHANNEL_HOST, cadena),
                             extra=item.extra))

    return itemlist


def listado_genero(item):
    logger.info("pelisalacarta.channels.pelispedia listado_genero")

    itemlist = []

    data = scrapertools.anti_cloudflare( CHANNEL_HOST+"buscar/?s=" , host=CHANNEL_HOST , headers=CHANNEL_DEFAULT_HEADERS )
    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;|<Br>|<BR>|<br>|<br/>|<br />|-\s", "", data)

    patron = '<select id="genres">.*?</select>'
    data = scrapertools.find_single_match(data, patron)

    patron = '<option name="([^"]+)".+?>(.*?)</option>'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for key, value in matches[1:]:

        cadena = "series/genero/"
        if item.extra == "movies":
            cadena = 'movies/all/?gender='
            cadena += key
        else:
            cadena += key+"/"

        itemlist.append(Item(channel=__channel__, action="listado", title=value, url=urlparse.urljoin(CHANNEL_HOST, cadena),
                             extra=item.extra))

    return itemlist


def listado_anio(item):
    logger.info("pelisalacarta.channels.pelispedia listado_anio")

    itemlist = []

    data = scrapertools.anti_cloudflare( CHANNEL_HOST+"buscar/?s=" , host=CHANNEL_HOST , headers=CHANNEL_DEFAULT_HEADERS )
    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;|<Br>|<BR>|<br>|<br/>|<br />|-\s", "", data)

    patron = '<select id="year">.*?</select>'
    data = scrapertools.find_single_match(data, patron)

    patron = '<option name="([^"]+)"'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for value in matches[1:]:

        cadena = "series/anio/"
        if item.extra == "movies":
            cadena = 'movies/all/?year='
            cadena += value
        else:
            cadena += value+"/"

        itemlist.append(Item(channel=__channel__, action="listado", title=value, url=urlparse.urljoin(CHANNEL_HOST, cadena),
                             extra=item.extra))

    return itemlist


def search(item, texto):
    logger.info("pelisalacarta.channels.pelispedia search texto={0}".format(texto))

    item.url = item.url + "%" + texto.replace(' ', '+') + "%"

    try:
        return listado(item)

    # Se captura la excepción, para no interrumpir al buscador global si un canal falla
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []


def listado(item):
    logger.info("pelisalacarta.channels.pelispedia listado")
    itemlist = []

    action = "findvideos"
    if item.extra == 'serie':
        action = "episodios"

    data = scrapertools.anti_cloudflare(item.url , host=CHANNEL_HOST , headers=CHANNEL_DEFAULT_HEADERS )
    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;|<Br>|<BR>|<br>|<br/>|<br />|-\s", "", data)
    # logger.info("data -- {}".format(data))

    patron = '<li[^>]+><a href="([^"]+)" alt="([^<]+).*?<img src="([^"]+).*?>.*?<span>\(([^)]+).*?' \
             '<p class="font12">(.*?)</p>'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for scrapedurl, scrapedtitle, scrapedthumbnail, scrapedyear, scrapedplot in matches:
        title = "{title} ({year})".format(title=scrapertools.unescape(scrapedtitle.strip()), year=scrapedyear)
        plot = scrapertools.entityunescape(scrapedplot)
        itemlist.append(Item(channel=__channel__, title=title, url=urlparse.urljoin(CHANNEL_HOST, scrapedurl), action=action,
                             thumbnail=scrapedthumbnail, plot=plot, context="",
                             show=scrapertools.unescape(scrapedtitle.strip()), extra=item.extra))

    # no se muestra ordenado porque la paginación de la página no se hace correctamente
    # itemlist.sort(key=lambda item: item.title)

    # numero de registros que se muestran por página, es fijo por cada paginación
    if len(matches) == 48:

        file_php = "more"
        tipo_serie = ""

        if item.extra == "movies":
            anio = scrapertools.find_single_match(item.url, "(?:year=)(\w+)")
            letra = scrapertools.find_single_match(item.url, "(?:letra=)(\w+)")
            genero = scrapertools.find_single_match(item.url, "(?:gender=|genre=)(\w+)")
            params = "letra={letra}&year={year}&genre={genero}".format(letra=letra, year=anio, genero=genero)

        else:
            tipo2 = scrapertools.find_single_match(item.url, "(?:series/|tipo2=)(\w+)")
            tipo_serie = "&tipo=serie"

            if tipo2 != "all":
                file_php = "letra"
                tipo_serie += "&tipo2="+tipo2

            genero = ""
            if tipo2 == "anio":
                genero = scrapertools.find_single_match(item.url, "(?:anio/|genre=)(\w+)")
            if tipo2 == "genero":
                genero = scrapertools.find_single_match(item.url, "(?:genero/|genre=)(\w+)")
            if tipo2 == "letra":
                genero = scrapertools.find_single_match(item.url, "(?:letra/|genre=)(\w+)")

            params = "genre={genero}".format(genero=genero)

        url = "http://www.pelispedia.tv/api/{file}.php?rangeStart=48&rangeEnd=48{tipo_serie}&{params}".\
            format(file=file_php, tipo_serie=tipo_serie, params=params)

        if "rangeStart" in item.url:
            ant_inicio = scrapertools.find_single_match(item.url, "rangeStart=(\d+)&")
            inicio = str(int(ant_inicio)+48)
            url = item.url.replace("rangeStart="+ant_inicio, "rangeStart="+inicio)

        itemlist.append(Item(channel=__channel__, action="listado", title=">> Página siguiente", extra=item.extra,
                             url=url))

    return itemlist


def episodios(item):
    logger.info("pelisalacarta.channels.pelispedia episodios")

    itemlist = []

    # Descarga la página
    data = scrapertools.anti_cloudflare(item.url , host=CHANNEL_HOST , headers=CHANNEL_DEFAULT_HEADERS )

    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;|<Br>|<BR>|<br>|<br/>|<br />|-\s", "", data)

    patron = '<div class="hero-image"><img src="([^"]+)"'
    fanart = scrapertools.find_single_match(data, patron)

    patron = '<div class="bpM18 bpS25 mt15 mb20 noPadding"><figure><img src="([^"]+)"'
    thumbnail = scrapertools.find_single_match(data, patron)

    patron = '<li class="clearfix gutterVertical20"><a href="([^"]+)".*?><small>(.*?)</small>.*?' \
             '<span class.+?>(.*?)</span>'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for scrapedurl, scrapedtitle, scrapedname in matches:
        logger.info("scrap {}".format(scrapedtitle))
        patron = 'Season\s+(\d),\s+Episode\s+(\d+)'
        match = re.compile(patron, re.DOTALL).findall(scrapedtitle)
        episode = match[0][1]
        if len(episode) == 1:
            episode = "0"+episode
        title = "{season}x{episode}: {name}".format(season=match[0][0], episode=episode,
                                                    name=scrapertools.unescape(scrapedname))

        itemlist.append(Item(channel=__channel__, title=title, url=scrapedurl, action="findvideos", fanart=fanart,
                             thumbnail=thumbnail, show=item.show, extra=item.extra))

    # TODO configurar en canal el orden los enlaces asc o desc?
    # itemlist.sort(key=lambda item: item.title)

    # Opción "Añadir esta serie a la biblioteca de XBMC"
    if config.get_library_support() and len(itemlist) > 0:
        itemlist.append(Item(channel=__channel__, title="Añadir esta serie a la biblioteca de XBMC", url=item.url,
                             action="add_serie_to_library", extra="episodios", show=item.show, category="Series"))

    return itemlist


def findvideos(item):
    logger.info("pelisalacarta.channels.pelispedia findvideos")

    itemlist = []

    # Descarga la página
    data = scrapertools.anti_cloudflare(item.url , host=CHANNEL_HOST , headers=CHANNEL_DEFAULT_HEADERS )
    data = re.sub(r"\n|\r|\t|\s{2}|&nbsp;|<Br>|<BR>|<br>|<br/>|<br />|-\s", "", data)

    patron = '<iframe src=".+?id=(\d+)'
    key = scrapertools.find_single_match(data, patron)
    data = scrapertools.anti_cloudflare( CHANNEL_HOST+'api/iframes.php?id={0}&update1.1'.format(key) , host=CHANNEL_HOST , headers=CHANNEL_DEFAULT_HEADERS )

    # Descarta la opción descarga que es de publicidad
    patron = '<a href="(?!http://go.ad2up.com)([^"]+)".+?><img src="/api/img/([^.]+)'
    matches = scrapertools.find_multiple_matches(data, patron)

    for scrapedurl, scrapedtitle in matches:
        # En algunos vídeos hay opción flash "vip" con varias calidades
        if "api/vip.php" in scrapedurl:
            data_vip = scrapertools.anti_cloudflare(scrapedurl , host=CHANNEL_HOST , headers=CHANNEL_DEFAULT_HEADERS )
            patron = '<a href="([^"]+)".+?><img src="/api/img/([^.]+).*?<span class="text">([^<]+)<'
            matches_vip = re.compile(patron, re.DOTALL).findall(data_vip)
            for url, titlevip, calidad in matches_vip:
                title = "Ver vídeo en ["+titlevip+"] "+calidad
                itemlist.append(Item(channel=__channel__, title=title, url=url, action="play"))
        else:
            title = "Ver vídeo en ["+scrapedtitle+"]"
            itemlist.append(Item(channel=__channel__, title=title, url=scrapedurl, action="play", extra=item.url))

    # Opción "Añadir esta serie a la biblioteca de XBMC"
    if item.extra == "movies" and config.get_library_support() and len(itemlist) > 0:
        itemlist.append(Item(channel=__channel__, title="Añadir esta película a la biblioteca de XBMC", url=item.url,
                             action="add_pelicula_to_library", extra="findvideos", fulltitle=item.title))

    return itemlist


def play(item):
    logger.info("pelisalacarta.channels.pelispedia play url={0}".format(item.url))

    itemlist = []
    # Para videos flash y html5
    if "pelispedia.tv" in item.url:
        key = scrapertools.find_single_match(item.url, 'index.php\?id=([^&]+)&sub=([^&]+)&.+?imagen=([^&]+)')
        subtitle = ""
        thumbnail = ""

        if len(key) > 2:
            thumbnail = key[2]
        if key[1] != "":
            subtitle = "{host}/sub/{sub}.srt".format(host=CHANNEL_HOST, sub=key[1])
        if "Player_Html5" in item.url:
            url = "http://www.pelispedia.tv/Pe_Player_Html5/index.php?id="+urllib.quote(key[0])
        else:
            url = "http://www.pelispedia.tv/Pe_flv_flsh/index.php?id="+urllib.quote(key[0])
        data = scrapertools.anti_cloudflare(url , host=CHANNEL_HOST , headers=CHANNEL_DEFAULT_HEADERS )
        # data = scrapertools.cache_page(url, post=post)
        media_urls = scrapertools.find_multiple_matches(data, '(?:link|url)":"([^"]+)"')
        # Si hay varias urls se añade la última que es la de mayor calidad
        if len(media_urls) > 0:
            url = media_urls[len(media_urls)-1].replace("\\", "")
            itemlist.append(Item(channel=__channel__, title=item.title, url=url, server="directo", action="play",
                                 subtitle=subtitle, thumbnail=thumbnail))

    elif "pelispedia.biz" in item.url:
        logger.info("estoy en el otro html5")
        key = scrapertools.find_single_match(item.url, 'v=([^&]+).+?imagen=([^&]+)')

        thumbnail = ""
        if len(key) > 1:
            thumbnail = key[1]

        data = scrapertools.anti_cloudflare(item.url , host=CHANNEL_HOST , headers=CHANNEL_DEFAULT_HEADERS )

        media_url = scrapertools.find_single_match(data, '"file":"([^"]+)"').replace("\\", "")
        sub = scrapertools.find_single_match(data, 'file:\s"([^"]+)".+?label:\s"Spanish"')
        itemlist.append(Item(channel=__channel__, title=item.title, url=media_url, server="directo", action="play",
                             subtitle=sub, thumbnail=thumbnail))

    else:
        itemlist = servertools.find_video_items(data=item.url)
        for videoitem in itemlist:
            videoitem.title = item.title
            videoitem.channel = __channel__

    return itemlist

