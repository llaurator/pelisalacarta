# -*- coding: utf-8 -*-
#------------------------------------------------------------
# pelisalacarta - XBMC Plugin
# http://blog.tvalacarta.info/plugin-xbmc/pelisalacarta/
#------------------------------------------------------------

import re
import xbmc
import xbmcgui

from core import config
from core import logger
from core import scrapertools
from core import tmdb
from platformcode import platformtools
from core.item import Item
from core.scrapertools import decodeHtmlentities as dhe
from threading import Thread

mainWindow = list()
ActoresWindow = None
TrailerWindow = None
relatedWindow = None
imagesWindow = None
ActorInfoWindow = None
BusquedaWindow = None
SearchWindows = list()

exit_loop = False


ACTION_SHOW_FULLSCREEN = 36
ACTION_GESTURE_SWIPE_LEFT = 511
ACTION_SELECT_ITEM = 7
ACTION_PREVIOUS_MENU = 10
ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_DOWN = 4
ACTION_MOVE_UP = 3
OPTION_PANEL = 6
OPTIONS_OK = 5


def start(item, recomendaciones=[], from_window=False):
    global mainWindow
    if from_window:
        global relatedWindow, ActorInfoWindow, ActoresWindow, BusquedaWindow, TrailerWindow, imagesWindow
        create = [relatedWindow, ActorInfoWindow, ActoresWindow, BusquedaWindow, TrailerWindow, imagesWindow]
        for window in create:
            window = None
        global exit_loop
        exit_loop = False
        global SearchWindows
        SearchWindows = list()
    
    dialog = platformtools.dialog_progress("[COLOR darkturquoise][B]Cargando nuevos datos[/B][/COLOR]", "[COLOR lightyellow]Buscando en  [/COLOR]"+ "[COLOR springgreen][B]Tmdb.......[/B][/COLOR]")

    principal_window = main(item=item, recomendaciones=recomendaciones, dialog=dialog, from_window=from_window)
    try:
        mainWindow.append(principal_window)
        principal_window.doModal()
    except:
        return


class main(xbmcgui.WindowDialog):
    def __init__(self, *args, **kwargs):
        self.item = kwargs.get('item')
        self.recomendaciones = kwargs.get('recomendaciones')
        self.dialog = kwargs.get('dialog')
        self.from_window = kwargs.get('from_window')

        if self.item.contentType == "movie":
            tipo = "película"
            tipo_busqueda = "movie"
            icono = "http://imgur.com/SenkyxF.png"
        else:
            tipo = "serie"
            tipo_busqueda = "tv"
            icono = "http://s6.postimg.org/hzcjag975/tvdb.png"

        if self.item.rating_filma:
            if "|" in self.item.show:
                self.item.show = ""
            self.infoLabels = self.item.info
            icono = self.item.icon
            rating_fa = self.item.rating_filma
            if tipo == "película":
                self.infoLabels["tmdb_id"] = self.item.extra.split("|")[1]
            else:
                self.infoLabels["tmdb_id"] = self.item.extra.split("|")[2]
            critica = self.item.critica
            rating = self.infoLabels.get("rating")
            titulo = self.infoLabels["title"]
            self.images = []
            thread1 = None
        else:
            info_copy = dict(self.item.infoLabels)
            self.item.infoLabels.pop("season", None)
            self.item.infoLabels.pop("episode", None)
            tmdb.set_infoLabels_item(self.item, True)
            self.infoLabels = self.item.infoLabels
            self.infoLabels["season"] = info_copy.get("season", None)
            self.infoLabels["episode"] = info_copy.get("episode", None)

            if not self.infoLabels["tmdb_id"]:
                self.dialog.close()
                platformtools.dialog_notification("Sin resultados", "No hay info de la %s solicitada" % tipo)
                global mainWindow
                self.close()
                del mainWindow
                return

            titulo = "[COLOR olive][B]%s[/B][/COLOR]" % self.infoLabels.get("title")
            try:
                if not self.infoLabels.get("rating"):
                    rating = "[COLOR crimson][B]Sin puntuación[/B][/COLOR]"
                elif self.infoLabels.get("rating") >= 5 and self.infoLabels.get("rating") < 8:
                    rating = "[COLOR springgreen][B]%s[/B][/COLOR]" % self.infoLabels["rating"]
                elif self.infoLabels.get("rating") >= 8:
                    rating = "[COLOR yellow][B]%s[/B][/COLOR]" % self.infoLabels["rating"]
                else:
                    rating = "[COLOR crimson][B]%s[/B][/COLOR]" % self.infoLabels["rating"]
            except:
                rating = "[COLOR crimson][B]%s[/B][/COLOR]" % self.infoLabels["rating"]

            self.dialog.update(40, '[COLOR teal]Registrando[/COLOR]'+'[COLOR yellow][B]  film[/B][/COLOR]'+'[COLOR floralwhite][B]affinity.......[/B][/COLOR]')
            critica, rating_fa, plot_fa = get_filmaf(self.item, self.infoLabels)
            if not self.infoLabels.get("plot") and plot_fa:
                self.infoLabels["plot"] = "[COLOR moccasin][B]%s[/B][/COLOR]" % plot_fa
            elif not self.infoLabels["plot"]:
                self.infoLabels["plot"] = "[COLOR yellow][B]Esta pelicula no tiene informacion...[/B][/COLOR]"
            else:
                self.infoLabels["plot"] = "[COLOR moccasin][B]%s[/B][/COLOR]" % self.infoLabels.get("plot")

            self.dialog.update(60, '[COLOR khaki]Indagando recomendaciones.......[/COLOR]')
            thread1 = Thread(target=get_recomendations,args=[self.item, self.infoLabels, self.recomendaciones])
            thread1.setDaemon(True) 
            thread1.start()

            if self.infoLabels.get("status") == "Ended" and tipo == "serie":
                status = "[COLOR aquamarine][B]Finalizada %s[/B][/COLOR]"
            elif self.infoLabels.get("status") and tipo == "serie":
                status = "[COLOR aquamarine][B]En emisión %s[/B][/COLOR]"
            else:
                status = "[COLOR aquamarine][B]%s[/B][/COLOR]"
            if self.infoLabels.get("tagline") and tipo == "serie":
                self.infoLabels["tagline"] = status % "("+self.infoLabels["tagline"]+")"
            elif not self.infoLabels.get("tagline") and tipo == "serie":
                self.infoLabels["tagline"] = status % "(Temporadas: %s)" % self.infoLabels.get("number_of_seasons", "---")
            else:
                self.infoLabels["tagline"] = status % self.infoLabels.get("tagline", "")

        self.images = {}
        thread2 = Thread(target=fanartv,args=[self.item, self.infoLabels, self.images])
        thread2.setDaemon(True) 
        thread2.start()

        if self.infoLabels["tmdb_id"]:
            otmdb = tmdb.Tmdb(id_Tmdb=self.infoLabels["tmdb_id"], tipo=tipo_busqueda)
            self.infoLabels["images"] = otmdb.result.get("images", {})
            for key, value in self.infoLabels["images"].items():
                if not value:
                    self.infoLabels["images"].pop(key)

            if not self.infoLabels.get("originaltitle"):
                self.infoLabels["originaltitle"] = otmdb.result.get("original_title", otmdb.result.get("original_name", ""))
            self.trailers = otmdb.get_videos()
            self.infoLabels["duration"] = int(otmdb.result.get("runtime", 0))
        else:
            self.trailers = []

        if self.item.contentType != "movie":
            self.dialog.update(60, '[COLOR teal]Recopilando imágenes en [/COLOR]'+ '[COLOR floralwhite][B]FAN[/B][/COLOR]'+'[COLOR slategray][B]ART.[/B][/COLOR]'+'[COLOR darkgray]TV.......[/COLOR]')
            try:
                ###Busca música serie
                titulo = re.sub('\[.*?\]', '', titulo)
                titulo = self.infoLabels.get("originaltitle", titulo)
                titulo = re.sub("'","", titulo)
                url_tvthemes = "http://televisiontunes.com/search.php?q=%s" % titulo.replace(' ', '+')

                data = scrapertools.downloadpage(url_tvthemes)
                page_theme =scrapertools.find_single_match(data, '<!-- sond design -->.*?<li><a href="([^"]+)"')

                if page_theme:
                    page_theme ="http://televisiontunes.com"+page_theme
                    data = scrapertools.downloadpage(page_theme)
                    song = scrapertools.get_match(data, '<form name="song_name_form">.*?type="hidden" value="(.*?)"')
                    song = song.replace(" ", "%20")
                    pl = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
                    pl.clear()
                    pl.add(song)
                    self.player = xbmc.Player()
                    self.player.play(pl)
            except:
                import traceback
                logger.info(traceback.format_exc())

        if xbmc.Player().isPlaying():
            self.dialog.update(80, '[COLOR teal]Afinado instrumentos en [/COLOR]'+ '[COLOR cyan][B]T[/B][/COLOR]'+'[COLOR paleturquoise][B]V[/B][/COLOR]'+'[COLOR floralwhite]tu[/COLOR]'+'[COLOR darkgray][B]n[/B][/COLOR]'+'[COLOR slategray][B]es[/B][/COLOR]')
        else:
            self.dialog.update(80, '[COLOR teal]Recopilando imágenes en [/COLOR]'+ '[COLOR floralwhite][B]FAN[/B][/COLOR]'+'[COLOR slategray][B]ART.[/B][/COLOR]'+'[COLOR darkgray]TV.......[/COLOR]')

        while thread2.isAlive():
            xbmc.sleep(100)
        if not self.infoLabels.get("fanart") and self.images:
            try:
                if self.item.contentType == "movie":
                    self.infoLabels["fanart"] = self.images.get("moviebackground", self.images.get("hdmovieclearart", self.images.get("movieart")))[0].get("url")
                else:
                    self.infoLabels["fanart"] = self.images.get("showbackground", self.images.get("hdclearart", self.images.get("clearart")))[0].get("url")
            except:
                self.infoLabels["fanart"] = 'http://i.imgur.com/XuXGXjN.jpg'
                import traceback
                logger.info(traceback.format_exc())
        elif self.infoLabels.get("season") and self.images.get("showbackground"):
            for imagen in self.images["showbackground"]:
                if imagen.get("season") == str(self.infoLabels.get("season", "")):
                    self.infoLabels["fanart"] = imagen["url"]
                    break

        if not self.infoLabels.get("fanart"):
            self.infoLabels["fanart"] = 'http://i.imgur.com/XuXGXjN.jpg'

        if self.images:
            try:
                if self.item.contentType == "movie":
                    self.infoLabels["thumbnail"] = self.images.get("hdmovielogo", self.images.get("movielogo", self.images.get("moviethumb")))[0].get("url")
                elif self.infoLabels.get("season") and self.images.get("seasonthumb"):
                    find = False
                    for imagen in self.images["seasonthumb"]:
                        if imagen.get("season") == str(self.infoLabels.get("season", "")):
                            self.infoLabels["thumbnail"] = imagen["url"]
                            find = True
                            break
                    if not find:
                        self.infoLabels["thumbnail"] = self.images.get("hdtvlogo", self.images.get("clearlogo", self.images.get("tvthumb")))[0].get("url")
                else:
                    self.infoLabels["thumbnail"] = self.images.get("hdtvlogo", self.images.get("clearlogo", self.images.get("tvthumb")))[0].get("url")
                self.infoLabels["thumbnail"] = self.infoLabels["thumbnail"].replace(" ", "%20")
            except:
                self.infoLabels["thumbnail"] = 'http://i.imgur.com/8K5f4Uo.png'
                import traceback
                logger.info(traceback.format_exc())
        elif not self.images and (not self.item.rating_filma or not self.infoLabels.get("thumbnail")):
            self.infoLabels["thumbnail"] = 'http://i.imgur.com/8K5f4Uo.png'

        self.name = re.sub(r'(\[.*?\])', '', self.infoLabels["title"])
        self.botones = []

        skin = xbmc.getSkinDir()
        self.fonts = get_fonts(skin)
        self.setCoordinateResolution(2)
        self.actorButton = xbmcgui.ControlButton(650, 50, 60, 60, '', font='Font40', alignment=0x00000006, noFocusTexture='http://i.imgur.com/yK4LCqB.png', focusTexture='http://s6.postimg.org/djdkrpz0x/starzen.png', focusedColor='0xFFAAAAAA')
        self.trailerButton = xbmcgui.ControlButton(550, 50, 60, 60, '', font='Font40', alignment=0x00000006, noFocusTexture='http://s6.postimg.org/dbs8k30r5/zentrailer.png', focusTexture='http://s6.postimg.org/jqr9gr7gx/zentrailerfocused.png')
        
        self.background = xbmcgui.ControlImage(-40, -40, 1500, 830, 'http://imgur.com/ur6H9Ps.png')
        self.title = xbmcgui.ControlTextBox(120, 0, 1130, 50)
        self.rating = xbmcgui.ControlTextBox(415, 37, 1040, 50)
        self.rating_filma = xbmcgui.ControlTextBox(417, 112, 1043, 50)
        self.tagline = xbmcgui.ControlFadeLabel(120, 70, 420, 45, self.fonts["12"])
        self.plot = xbmcgui.ControlTextBox(117, 150, 1056, 150)
        self.critica = xbmcgui.ControlTextBox(20, 386, 1056, 100, self.fonts["12"])
        self.fanart = xbmcgui.ControlImage(-40, -40, 1500, 830, self.infoLabels.get("fanart", ""))
        self.critica_image = xbmcgui.ControlImage(120, 300, 200, 90, 'http://imgur.com/kGmaIER.png')
        self.icon = xbmcgui.ControlImage(360, 30, 40, 40, icono)
        self.fa_icon = xbmcgui.ControlImage(350, 100, 60, 60, "http://s6.postimg.org/6yhe5fgy9/filma.png")

        self.addControl(self.fanart)
        self.fanart.setAnimations([('conditional', 'effect=rotatey start=100% end=0% time=1500 condition=true',),('unfocus', 'effect=zoom start=110% end=100% time=1000 tween=elastic easing=out',),('WindowClose','effect=rotatey delay= 1000 start=0% end=-300% time=800 condition=true',)])

        self.addControl(self.background)
        self.addControl(self.critica_image)
        self.critica_image.setAnimations([('conditional', 'effect=rotatey center=500 start=300% end=0% time=3000 condition=true ',),('unfocus', 'effect=zoom start=110% end=100% time=1000 tween=elastic easing=out',), ('focus', 'effect=zoom start=80% end=110% time=700',),('WindowClose','effect=rotatey center=500 start=0% end=-300% time=800 condition=true',)])
        self.addControl(self.trailerButton)
        self.botones.append(self.trailerButton)
        self.trailerButton.setAnimations([('conditional', 'effect=slide start=-1500% end=0% delay=1200 time=4000 condition=true tween=elastic',),('unfocus', 'effect=zoom start=110% end=100% time=1000 tween=elastic easing=out',), ('focus', 'effect=zoom start=80% end=110% time=700',),('WindowClose','effect=slide start=0% end=-1500% time=800 condition=true',)])
        self.addControl(self.actorButton)
        self.botones.append(self.actorButton)
        self.actorButton.setAnimations([('conditional', 'effect=slide start=1500% end=0% delay=1200 time=4000 condition=true tween=elastic',),('unfocus', 'effect=zoom start=110% end=100% time=1000 tween=elastic easing=out',), ('focus', 'effect=zoom start=80% end=110% time=700' ,),('WindowClose','effect=slide start=0% end=1500% time=800 condition=true',)])

        self.setFocus(self.trailerButton)
        self.addControl(self.title)
        self.title.setAnimations([('conditional', 'effect=fade start=0% end=100% delay=1500 time=1500 condition=true',),('WindowClose','effect=fade start=100% end=0% time=800 condition=true',)])
        self.addControl(self.tagline)
        self.tagline.setAnimations([('conditional', 'effect=fade start=0% end=100% delay=2000 time=1500 condition=true',),('WindowClose','effect=fade start=100% end=0% time=800 condition=true',)])
        if self.item.contentType == "movie" and self.infoLabels.get("duration", 0):
            self.duration = xbmcgui.ControlTextBox(120, 100, 420, 45, self.fonts["12"])
            self.addControl(self.duration)
            self.duration.setAnimations([('conditional', 'effect=fade start=0% end=100% delay=2000 time=1500 condition=true',),('WindowClose','effect=fade start=100% end=0% time=800 condition=true',)])    
            self.duration.setText("[COLOR mediumturquoise][B]Duración: %s minutos[/B][/COLOR]" % self.infoLabels["duration"])
        self.addControl(self.rating)
        self.rating.setAnimations([('conditional', 'effect=rotatey start=100% end=0% delay=3000 time=1500 condition=true',),('WindowClose','effect=rotatey start=0% end=100% time=800 condition=true',)])
        self.addControl(self.rating_filma)
        self.rating_filma.setAnimations([('conditional', 'effect=rotatey start=100% end=0% delay=3000 time=1500 condition=true',),('WindowClose','effect=rotatey start=0% end=100% time=800 condition=true',)])
        self.addControl(self.plot)
        self.plot.setAnimations([('conditional', 'effect=slide delay=2000 start=1500 time=3600 tween=elastic easing=inout condition=true',),('WindowClose','effect=zoom center=auto start=100% end=0% time=800 condition=true',)])
        self.addControl(self.critica)
        self.critica.setAnimations([('conditional', 'effect=slide delay=1800 start=-1500% end=100% time=3600 tween=elastic easing=inout condition=true',),('WindowClose','effect=slide start=100% end=-1500% time=800 condition=true',)])

        if not self.infoLabels.get("images") and not self.images:
            self.thumbnail = xbmcgui.ControlImage(813, 0, 390, 150, 'http://i.imgur.com/oMjtYni.png')
            self.addControl(self.thumbnail)
            self.thumbnail.setAnimations([('conditional','effect=zoom delay=2000 center=auto start=0 end=100 time=800 condition=true',),('conditional','effect=rotate delay=2000 center=auto aceleration=6000 start=0% end=360% time=800 condition=true',),('WindowClose','effect=zoom start=100% end=0% time=600 condition=true',)])
        else:
            self.thumbnail = xbmcgui.ControlButton(813, 0, 390, 150, '', self.infoLabels.get("thumbnail", ""), self.infoLabels.get("thumbnail", ""))
            self.addControl(self.thumbnail)
            self.thumbnail.setAnimations([('conditional','effect=zoom delay=2000 center=auto start=0 end=100 time=800 condition=true',),('conditional','effect=rotate delay=2000 center=auto aceleration=6000 start=0% end=360% time=800 condition=true',),('unfocus', 'effect=zoom start=105% end=100% time=1000 tween=elastic easing=out',), ('focus', 'effect=zoom start=80% end=100% time=700' ,),('WindowClose','effect=zoom start=100% end=0% time=600 condition=true',)])
            self.botones.append(self.thumbnail)

        self.addControl(self.icon)
        self.icon.setAnimations([('conditional','effect=slide start=0,-700 delay=2000 time=2500 tween=bounce condition=true',),('conditional','effect=rotate center=auto start=0% end=360% delay=3000 time=2500 tween=bounce condition=true',),('WindowClose','effect=slide end=0,-700% time=1000 condition=true',)])
        self.addControl(self.fa_icon)
        self.fa_icon.setAnimations([('WindowOpen','effect=slide start=0,-700 delay=3000 time=2500 tween=bounce condition=true',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])

        self.title.setText(titulo)
        self.tagline.addLabel(self.infoLabels.get("tagline"))
        self.rating.setText(rating)
        self.rating_filma.setText(rating_fa)

        try:
            self.plot.autoScroll(11000, 6000, 30000)
            self.critica.autoScroll(11000, 2500, 13000)
        except:
            xbmc.executebuiltin('Notification([COLOR red][B]Actualiza Kodi a su última versión[/B][/COLOR], [COLOR skyblue]para mejor info[/COLOR],8000, "http://i.imgur.com/mHgwcn3.png")')
        self.plot.setText(dhe(self.infoLabels.get("plot", "")))
        self.critica.setText(critica)
        self.critica_butt = xbmcgui.ControlButton(20, 386, 1056, 100, '', '', '')
        self.addControl(self.critica_butt)

        xbmc.sleep(200)
        self.mas_pelis = 8
        self.idps = []
        self.botones_maspelis = []
        self.focus = -1
        i = 0
        count = 0
        self.btn_left = xbmcgui.ControlButton(90, 490, 70, 29, '', "http://s6.postimg.org/i3pnobu6p/redarrow.png", "http://s6.postimg.org/i3pnobu6p/redarrow.png")
        self.addControl(self.btn_left)
        self.btn_left.setAnimations([('conditional','effect=zoom start=-100 end=100 delay=5000 time=2000 condition=true tween=bounce' ,),('conditional','effect=zoom start=720,642,70,29 end=640,642,69,29 time=1000 loop=true tween=bounce condition=Control.HasFocus('+str(self.btn_left.getId())+')',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])
        self.btn_left.setVisible(False)
        self.botones.append(self.btn_left)
        if thread1:
            while thread1.isAlive():
                xbmc.sleep(100)
        for idp, peli, thumb in self.recomendaciones:
            if self.item.contentType == "movie":
                peli = "[COLOR yellow][B]"+peli+"[/B][/COLOR]"
            else:
                peli = "[COLOR slategray][B]"+peli+"[/B][/COLOR]"
            if count % 8 == 0:
                i=0
            self.image = xbmcgui.ControlButton(65+i, 538, 135, 160, '', thumb, thumb)
            self.neon = xbmcgui.ControlImage(60+i, 525, 145, 186, "http://s6.postimg.org/x0jspnxch/buttons.png")
            fadelabel = xbmcgui.ControlFadeLabel(67+i, 698, 135, 50)
            self.botones.append(self.image)
            if len(self.recomendaciones) != 0:
                self.tpi = xbmcgui.ControlImage(200, 490, 100, 41, 'http://imgur.com/GNP2QcB.png')
                self.addControl(self.tpi)
                self.tpi.setAnimations([('conditional', 'effect=rotatey start=200 end=0 delay=6200 time=900 tween=elastic condition=true',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',), ('focus', 'effect=rotate center=auto start=0% end=360% time=650 tween=bounce',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])
            if count < 8:
             
                self.addControl(self.image)
                self.image.setAnimations([('conditional', 'effect=rotatey start=200 end=0 delay=6200 time=900 tween=elastic condition=true',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',), ('focus', 'effect=rotate center=auto start=0% end=360% time=650 tween=bounce',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])
                self.addControl(fadelabel)
                fadelabel.addLabel(peli)
                fadelabel.setAnimations([('conditional', 'effect=rotatey start=200 end=0 delay=6200 time=900 tween=elastic condition=true',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])

                self.addControl(self.neon)
                self.neon.setVisibleCondition('[Control.HasFocus('+str(self.image.getId())+')]')
                self.neon.setAnimations([('conditional', 'effect=rotate center=auto start=0% end=360% time=650 tween=bounce condition=Control.HasFocus('+str(self.image.getId())+')',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])

            self.idps.append([self.image, peli, idp, thumb])
            self.botones_maspelis.append([self.image, self.neon, fadelabel, peli])

            i += 150
            count += 1

        xbmc.sleep(200)
        self.btn_right = None
        if len(self.recomendaciones) > 8:
            self.btn_right = xbmcgui.ControlButton(1150, 495, 60, 27, '', "http://s6.postimg.org/j4uhr70k1/greenarrow.png", "http://s6.postimg.org/j4uhr70k1/greenarrow.png")
            self.addControl(self.btn_right)
            self.btn_right.setAnimations([('conditional','effect=slide start=-3000 end=0 delay=6200 time=2000 condition=true tween=bounce' ,),('conditional','effect=zoom start=230,490, 60, 27, 29 end=1230,642,61,27 time=1000 loop=true tween=bounce condition=Control.HasFocus('+str(self.btn_right.getId())+')',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])
            self.botones.append(self.btn_right)
        xbmc.sleep(200)

        self.lupam = xbmcgui.ControlImage(820, 320, 60, 60, "http://imgur.com/VDdB0Uw.png")
        self.addControl(self.lupam)
        self.lupam.setAnimations([('conditional', 'effect=slide start=1500 delay=7020 time=200 tween=elastic condition=true',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])

        self.global_search = xbmcgui.ControlButton(916, 320, 140, 53, '', 'http://imgur.com/hoOvpHV.png', 'http://imgur.com/hoOvpHV.png')
        self.addControl(self.global_search)
        self.global_search.setAnimations([('conditional', 'effect=slide start=0,700 delay=6200 time=900 condition=true',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',),('focus','effect=zoom center=auto end=130% reversible=false',),('WindowClose','effect=slide end=0,700 time=1000 condition=true',)])
        self.botones.insert(3, self.global_search)
        self.buscar = None
        if self.from_window:
            canal = self.item.from_channel
            if not canal:
                canal = self.item.channel
            channel = __import__('channels.%s' % canal, None, None, ["channels.%s" % canal])
            if hasattr(channel, 'search'):
                if not self.item.thumb_busqueda:
                    from core import channeltools
                    self.item.thumb_busqueda = channeltools.get_channel_parameters(canal)["thumbnail"]
                self.buscar = xbmcgui.ControlButton(1095, 320, 140, 53, '', self.item.thumb_busqueda, self.item.thumb_busqueda)
                self.addControl(self.buscar)
                self.botones.insert(4, self.buscar)
                self.buscar.setAnimations([('conditional', 'effect=slide start=0,700 delay=6200 time=900 condition=true',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',),('focus','effect=zoom center=auto end=130% reversible=false',),('WindowClose','effect=slide end=0,700 time=1000 condition=true',)])
        xbmc.sleep(200)
        self.dialog.close()


    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU or action == ACTION_GESTURE_SWIPE_LEFT or action == 110 or action == 92:
            global mainWindow
            xbmc.executebuiltin('xbmc.PlayMedia(Stop)')
            self.close()
            mainWindow.pop()
            if not mainWindow:
                del mainWindow
            else:
                xbmc.sleep(800)
                mainWindow[-1].doModal()

        if action == ACTION_MOVE_RIGHT or action == ACTION_MOVE_DOWN :
            if self.focus < len(self.botones)-1:
                self.focus += 1
                while True:
                    id_focus = str(self.botones[self.focus].getId())
                    if xbmc.getCondVisibility('[Control.IsVisible('+id_focus+')]'):
                        self.setFocus(self.botones[self.focus])
                        break
                    self.focus += 1
                    if self.focus == len(self.botones):
                        break

        if action == ACTION_MOVE_LEFT or action == ACTION_MOVE_UP :
            if self.focus > 0:
                self.focus -= 1
                while True:
                    id_focus = str(self.botones[self.focus].getId())
                    if xbmc.getCondVisibility('[Control.IsVisible('+id_focus+')]'):
                        self.setFocus(self.botones[self.focus])
                        break
                    self.focus -= 1
                    if self.focus == len(self.botones):
                        break

        if action == 105 or action == 6:
            for boton, peli, id, poster2 in self.idps:
                try:
                    if self.getFocusId() == boton.getId() and self.btn_right:
                        self.focus = len(self.botones) - 1
                        xbmc.executebuiltin('SendClick(%s)' % self.btn_right.getId())
                except:
                    pass

        if action == 104 or action == 5:
            for boton, peli, id, poster2 in self.idps:
                try:
                    if self.getFocusId() == boton.getId() and self.btn_left:
                        self.setFocus(self.btn_left)
                        xbmc.executebuiltin('SendClick(%s)' % self.btn_left.getId())
                except:
                    pass


    def onControl(self, control):
        if control == self.actorButton:
            global ActoresWindow
            ActoresWindow = Actores('DialogSelect.xml', config.get_runtime_path(), tmdb_id=self.infoLabels["tmdb_id"], item=self.item, fonts=self.fonts)
            ActoresWindow.doModal()

        elif control == self.trailerButton:
            global TrailerWindow
            item = self.item.clone(thumbnail=self.infoLabels.get("thumbnail", ""), contextual=True, contentTitle=self.name, windowed=True, infoLabels=self.infoLabels)
            TrailerWindow = Trailer('TrailerWindow.xml', config.get_runtime_path()).Start(item, self.trailers)

        elif control == self.thumbnail:
            global imagesWindow
            imagesWindow = images(fanartv=self.images, tmdb=self.infoLabels["images"])
            imagesWindow.doModal()

        elif control == self.buscar or control == self.global_search:
            if control == self.buscar:
                check_busqueda = "no_global"
                try:
                    canal = self.item.from_channel
                    if not canal:
                        canal = self.item.channel
                    channel = __import__('channels.%s' % canal, None, None, ["channels.%s" % canal])
                    itemlist = channel.search(self.item.clone(), self.infoLabels.get("title"))
                    if not itemlist and self.infoLabels.get("originaltitle"):
                        itemlist = channel.search(self.item.clone(), self.infoLabels.get("originaltitle", ""))
                except:
                    import traceback
                    logger.info(traceback.format_exc())
            else:
                check_busqueda = "global"
                itemlist = busqueda_global(self.item, self.infoLabels)
                if len(itemlist) == 1 and self.infoLabels.get("originaltitle"):
                    itemlist = busqueda_global(self.item, self.infoLabels, org_title=True)
            if itemlist:
                global BusquedaWindow
                BusquedaWindow = Busqueda('DialogSelect.xml', config.get_runtime_path(), itemlist=itemlist, item=self.item)
                BusquedaWindow.doModal()
            else:
                if check_busqueda == "no_global":
                   self.buscar.setVisible(False)
                   self.notfound = xbmcgui.ControlImage(800, 520, 300, 120, "http://imgur.com/V1xs9pT.png")
                   self.addControl(self.notfound)
                   self.notfound.setAnimations([('conditional', 'effect=zoom center=auto start=500% end=0% time=2000 condition=true',)])
                else:
                   self.global_search.setVisible(False)
                   self.notfound = xbmcgui.ControlImage(800, 520, 300, 120, "http://imgur.com/V1xs9pT.png")
                   self.addControl(self.notfound)
                   self.notfound.setAnimations([('conditional', 'effect=zoom center=auto start=500% end=0% time=2000 condition=true',)])
        elif control == self.btn_right:
            try:
                i = 1
                count = 0
                for afoto, neon, fadelabel, peli in self.botones_maspelis:
                    if i > self.mas_pelis - 8 and i <= self.mas_pelis and count < 8:
                        self.removeControls([afoto, neon, fadelabel])
                        count += 1
                    elif i > self.mas_pelis and count < 16:
                        self.addControl(afoto)
                        afoto.setAnimations([('conditional', 'effect=rotatey start=200 end=0 time=900 delay=200 tween=elastic condition=true',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',), ('focus', 'effect=rotate center=auto start=0% end=360% time=650 tween=bounce',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])
                        self.addControl(fadelabel)
                        fadelabel.addLabel(peli)
                        fadelabel.setAnimations([('conditional', 'effect=rotatey start=200 end=0 time=900 tween=elastic condition=true',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])

                        self.addControl(neon)
                        neon.setVisibleCondition('[Control.HasFocus('+str(afoto.getId())+')]')
                        neon.setAnimations([('conditional', 'effect=rotate center=auto start=0% end=360% time=650 tween=bounce condition=Control.HasFocus('+str(afoto.getId())+')',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])

                        count += 1
                        self.mas_pelis += 1
                        xbmc.sleep(120)
                    i += 1

                if self.mas_pelis > 8 and self.mas_pelis < 17:
                    self.btn_left.setVisible(True)
                if len(self.botones_maspelis) < self.mas_pelis + 1:
                    self.btn_right.setVisible(False)
                    self.setFocus(self.btn_left)
                    self.focus = 4
                else:
                    self.focus = len(self.botones) - 1
                    self.setFocus(self.btn_right)
                xbmc.sleep(300)
            except:
                pass
        elif control == self.btn_left:
            try:
                i = 1
                count = 0

                if self.mas_pelis == len(self.botones_maspelis):
                    self.btn_right.setVisible(True)

                len_pelis = self.mas_pelis
                for afoto, neon, fadelabel, peli in self.botones_maspelis:
                    resta = 8 + (len_pelis%8)
                    if resta == 8:
                        resta = 16
                    resta2 = len_pelis%8
                    if not resta2:
                        resta2 = 8
                    if i > len_pelis - resta and count < 8:
                        self.addControl(afoto)
                        afoto.setAnimations([('conditional', 'effect=rotatey start=200 end=0 time=900 tween=elastic condition=true',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',), ('focus', 'effect=rotate center=auto start=0% end=360% time=650 tween=bounce',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])
                        self.addControl(fadelabel)
                        fadelabel.addLabel(peli)
                        fadelabel.setAnimations([('conditional', 'effect=rotatey start=200 end=0 time=900 tween=elastic condition=true',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])

                        self.addControl(neon)
                        neon.setVisibleCondition('[Control.HasFocus('+str(afoto.getId())+')]')
                        neon.setAnimations([('conditional', 'effect=rotate center=auto start=0% end=360% time=650 tween=bounce condition=Control.HasFocus('+str(afoto.getId())+')',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])
                        count += 1
                    elif i > len_pelis - resta2 and i <= len_pelis and count < 16:
                        self.removeControls([afoto, neon, fadelabel])
                        count += 1
                        self.mas_pelis -= 1
                    i += 1

                if self.mas_pelis == 8:
                    self.btn_left.setVisible(False)
                    self.focus = -1
                    xbmc.executebuiltin('Action(Left)')
            except:
                pass
        else:
            for boton, peli, id, poster2 in self.idps:
                if control == boton:
                    tipo = self.item.contentType
                    if tipo != "movie":
                        tipo = "tv"
                    new_tmdb = tmdb.Tmdb(id_Tmdb=id, tipo=tipo)
                    new_infolabels = new_tmdb.get_infoLabels()
                    trailers = new_tmdb.get_videos()

                    new_infolabels["cast"] = new_tmdb.result.get("credits_cast", [])
                    new_infolabels["crew"] = new_tmdb.result.get("credits_crew", [])
                    new_infolabels["created_by"] = new_tmdb.result.get("created_by", [])
                    global relatedWindow
                    relatedWindow = related(item=self.item, infolabels=new_infolabels, fonts=self.fonts, trailers=trailers)
                    relatedWindow.doModal()


class related(xbmcgui.WindowDialog):
    def __init__(self, *args, **kwargs):
        self.item = kwargs.get("item")
        self.infoLabels = kwargs.get("infolabels")
        self.fonts = kwargs.get("fonts")
        self.trailers = kwargs.get("trailers")

        try:
            if not self.infoLabels.get("rating"):
                rating = "[COLOR crimson][B]Sin puntuación[/B][/COLOR]"
            elif self.infoLabels["rating"] >= 5 and self.infoLabels["rating"] < 8:
                rating = "[COLOR springgreen][B]%s[/B][/COLOR]" % self.infoLabels["rating"]
            elif self.infoLabels["rating"] >= 8:
                rating = "[COLOR fuchsia][B]%s[/B][/COLOR]" % self.infoLabels["rating"]
            else:
                rating = "[COLOR crimson][B]%s[/B][/COLOR]" % self.infoLabels["rating"]
        except:
            rating = "[COLOR crimson][B]%s[/B][/COLOR]" % self.infoLabels["rating"]

        images = fanartv(self.item, self.infoLabels)
        if not self.infoLabels.get("fanart"):
            try:
                if self.item.contentType == "movie":
                    self.infoLabels["fanart"] = images.get("moviebackground", images.get("hdmovieclearart", images.get("movieart")))[0].get("url")
                else:
                    self.infoLabels["fanart"] = images.get("showbackground", images.get("hdclearart", images.get("clearart")))[0].get("url")
            except:
                import traceback
                logger.info(traceback.format_exc())

        try:
            if self.item.contentType == "movie":
                self.infoLabels["thumbnail"] = images.get("hdmovielogo", images.get("movielogo"))[0].get("url")
            elif self.infoLabels["season"]:
                self.infoLabels["thumbnail"] = images.get("seasonthumb", images.get("tvthumb", images.get("hdtvlogo")))[0].get("url")
            else:
                self.infoLabels["thumbnail"] = images.get("hdtvlogo", images.get("tvthumb"))[0].get("url")
        except:
            import traceback
            logger.info(traceback.format_exc())

        self.setCoordinateResolution(2)
        self.background = xbmcgui.ControlImage(78, 50, 1053, 634, self.infoLabels.get("fanart", "http://s6.postimg.org/fflvear2p/nofanart.png"))
        self.addControl(self.background)
        self.background.setAnimations([('conditional', 'effect=slide start=1000% end=100% delay=670 time=2500 condition=true',),('WindowClose','effect=slide end=-2000% time=1000 condition=true',)])

        self.shadow = xbmcgui.ControlImage(75, 43, 1061, 649, 'http://s6.postimg.org/k05dw264x/marc_fanart.png')
        self.addControl(self.shadow)
        self.shadow.setAnimations([('conditional', 'effect=slide start=1000% end=100% delay=660 time=2500 condition=true',),('WindowClose','effect=slide end=-2000% time=1000 condition=true',)])
        self.star = xbmcgui.ControlImage(955, 55, 67, 67, "http://s6.postimg.org/jzn0d3clt/star.png")
        self.addControl(self.star)
        self.star.setAnimations([('conditional','effect=slide delay=6000 start=2000 time=800 condition=true',),('WindowClose','effect=slide end=0,-700% time=1000 condition=true',)])

        self.puntuacion_peli = xbmcgui.ControlTextBox(977, 78, 35, 35, self.fonts["12"])
        self.addControl(self.puntuacion_peli)
        self.puntuacion_peli.setText(rating)
        self.puntuacion_peli.setAnimations([('conditional','effect=slide delay=6000 start=2000 time=800 condition=true',),('WindowClose','effect=slide end=0,-700% time=1000 condition=true',)])

        self.info = "[COLOR lemonchiffon]%s[/COLOR]" % self.infoLabels.get("plot", "Sin información...")
        self.info_peli = xbmcgui.ControlTextBox(455, 120, 750, 234)
        self.addControl(self.info_peli)

        try:
            self.info_peli.autoScroll(7000, 6000, 30000)
        except:
            xbmc.executebuiltin('Notification([COLOR red][B]Actualiza Kodi a su última versión[/B][/COLOR], [COLOR skyblue]para mejor info[/COLOR],8000, "http://i.imgur.com/mHgwcn3.png")')
        self.info_peli.setText(self.info)
        self.info_peli.setAnimations([('conditional', 'effect=fade start=0% end=100%  delay=3600 time=800  condition=true',),('conditional', 'effect=slide  delay=1000  start=0,-500  delay=2600 time=2200 tween=bounce condition=true',),('WindowClose','effect=fade end=0% time=1000 condition=true',)])

        self.poster_peli = xbmcgui.ControlImage(210, 90, 230, 260, self.infoLabels.get("thumbnail", ""))
        self.addControl(self.poster_peli)
        self.poster_peli.setAnimations([('conditional', 'effect=zoom center=auto start=0% end=100%  delay=2000 time=3000 tween=bounce condition=true',),('WindowClose','effect=zoom end=0% time=1000 condition=true',)])

        if self.infoLabels.get("status") == "Ended" and self.item.contentType != "movie":
            status = "[COLOR aquamarine][B]Finalizada %s[/B][/COLOR]"
        elif self.infoLabels.get("status") and self.item.contentType != "movie":
            status = "[COLOR aquamarine][B]En emisión %s[/B][/COLOR]"
        else:
            status = "[COLOR aquamarine][B]%s[/B][/COLOR]"

        if self.infoLabels.get("tagline") and self.item.contentType != "movie":
            self.infoLabels["tagline"] = status % "("+self.infoLabels["tagline"]+")"
        else:
            self.infoLabels["tagline"] = status % self.infoLabels.get("tagline", "")

        if self.infoLabels.get("tagline"):
            self.tagline_peli = xbmcgui.ControlFadeLabel(290, 55, 490, 260)
            self.addControl(self.tagline_peli)
            self.tagline_peli.addLabel(self.infoLabels["tagline"])
            self.tagline_peli.setAnimations([('conditional', 'effect=fade center=auto start=0% end=100%  delay=3800 time=2000  condition=true',),('WindowClose','effect=fade end=0% time=500 condition=true',)])

        if self.infoLabels.get("title", self.infoLabels.get("originaltitle")):
            self.title_peli = xbmcgui.ControlFadeLabel(455, 85, 320, 430)
            self.addControl(self.title_peli)
            self.title_peli.addLabel("[COLOR yellow][B]%s[/B][/COLOR]" % self.infoLabels.get("title", self.infoLabels.get("originaltitle")))
            self.title_peli.setAnimations([('conditional', 'effect=fade start=0% end=100%  delay=2500 time=5000  condition=true',),('WindowClose','effect=fade end=0% time=1000 condition=true',)])

        self.gt_peli = xbmcgui.ControlTextBox(210, 385, 1100, 60, self.fonts["12"])
        self.addControl(self.gt_peli)
        self.gt_peli.setText("[COLOR limegreen][B]Género: [/B][/COLOR]")
        self.gt_peli.setAnimations([('conditional','effect=slide start=0,-7000 delay=5750 time=700 condition=true tween=circle easing=in',),('WindowClose','effect=slide end=0,-7000% time=700 condition=true',)])

        self.genero_peli = xbmcgui.ControlFadeLabel(271, 385, 400, 60, self.fonts["12"])
        self.addControl(self.genero_peli)
        self.genero_peli.addLabel("  [COLOR yellowgreen][B]%s[/B][/COLOR]" % self.infoLabels.get("genre", "---"))
        self.genero_peli.setAnimations([('conditional','effect=slide start=0,-7000 delay=5750 time=700 condition=true tween=circle easing=in',),('WindowClose','effect=slide end=0,-7000% time=700 condition=true',)])

        self.pt_peli = xbmcgui.ControlTextBox(210, 410, 307, 60, self.fonts["12"])
        self.addControl(self.pt_peli)
        self.pt_peli.setText("[COLOR limegreen][B]Productora: [/B][/COLOR]")
        self.pt_peli.setAnimations([('conditional','effect=slide start=0,-7000 delay=5700 time=700 condition=true tween=circle easing=in',),('WindowClose','effect=slide end=0,-7000% delay=100 time=700 condition=true',)])

        self.productora_peli = xbmcgui.ControlFadeLabel(310, 410, 400, 60, self.fonts["12"])
        self.addControl(self.productora_peli)
        self.productora_peli.addLabel("[COLOR yellowgreen][B]%s[/B][/COLOR]" % self.infoLabels.get("studio", "---"))
        self.productora_peli.setAnimations([('conditional','effect=slide start=0,-700 delay=5700 time=700 condition=true tween=circle easing=in',),('WindowClose','effect=slide end=0,-7000% delay=100 time=700 condition=true',)])

        self.paist_peli = xbmcgui.ControlTextBox(210, 435, 400, 60, self.fonts["12"])
        self.addControl(self.paist_peli)
        self.paist_peli.setText("[COLOR limegreen][B]País: [/B][/COLOR]")
        self.paist_peli.setAnimations([('conditional','effect=slide start=0,-700 delay=5650 time=700 condition=true tween=circle easing=in',),('WindowClose','effect=slide end=0,-7000% delay=200 time=700 condition=true',)])

        self.pais_peli = xbmcgui.ControlFadeLabel(247, 435, 400, 60, self.fonts["12"])
        self.addControl(self.pais_peli)
        self.pais_peli.addLabel("  [COLOR yellowgreen][B]%s[/B][/COLOR]" % self.infoLabels.get("country", "---"))
        self.pais_peli.setAnimations([('conditional','effect=slide start=0,-700 delay=5650 time=700 condition=true tween=circle easing=in',),('WindowClose','effect=slide end=0,-7000% delay=200 time=700 condition=true',)])

        self.ft_peli = xbmcgui.ControlTextBox(210, 460, 1100, 60, self.fonts["12"])
        self.addControl(self.ft_peli)
        self.ft_peli.setText("[COLOR limegreen][B]Estreno: [/B][/COLOR]")
        self.ft_peli.setAnimations([('conditional','effect=slide start=0,-700 delay=5600 time=700 condition=true tween=circle easing=in',),('WindowClose','effect=slide end=0,-7000% delay=300 time=700 condition=true',)])

        self.fecha_peli = xbmcgui.ControlFadeLabel(273, 460, 400, 60, self.fonts["12"])
        self.addControl(self.fecha_peli)
        release_date = "  [COLOR yellowgreen][B]%s[/B][/COLOR]" % self.infoLabels.get("release_date", self.infoLabels.get("premiered", "---"))
        self.fecha_peli.addLabel(release_date)
        self.fecha_peli.setAnimations([('conditional','effect=slide start=0,-700 delay=5600 time=700 condition=true tween=circle easing=in',),('WindowClose','effect=slide end=0,-7000% delay=300 time=700 condition=true',)])

        if self.infoLabels.get("number_of_seasons"):
            self.seasons_txt = xbmcgui.ControlTextBox(210, 485, 200, 60, self.fonts["12"])
            self.addControl(self.seasons_txt)
            self.seasons_txt.setText("[COLOR limegreen][B]Temporadas/Episodios: [/B][/COLOR]")
            self.seasons_txt.setAnimations([('conditional','effect=slide start=0,-700 delay=5600 time=700 condition=true tween=circle easing=in',),('WindowClose','effect=slide end=0,-7000% time=700 condition=true',)])

            self.seasons = xbmcgui.ControlFadeLabel(413, 485, 400, 60, self.fonts["12"])
            self.addControl(self.seasons)
            temporadas = "  [COLOR yellowgreen][B]%s/%s[/B][/COLOR]" % (self.infoLabels.get("number_of_seasons"), self.infoLabels.get("number_of_episodes", "---"))
            self.seasons.addLabel(temporadas)
            self.seasons.setAnimations([('conditional','effect=slide start=0,-700 delay=5600 time=700 condition=true tween=circle easing=in',),('WindowClose','effect=slide end=0,-7000% delay=300 time=700 condition=true',)])

        i = 0
        sleep = 0
        for actor in self.infoLabels.get("cast", [])[:5]:
            image = "https://image.tmdb.org/t/p/original"
            if actor.get("profile_path"):
                image += actor["profile_path"]
            else:
                image = "http://i.imgur.com/xQRgLkO.jpg"
            self.actor = xbmcgui.ControlImage(215+i, 529, 63, 63, image)
            self.addControl(self.actor)
            self.actor.setAnimations([('conditional','effect=zoom center=auto start=0% end=100% delay=5800 time=1500 tween=bounce condition=true ',),('WindowClose','effect=zoom end=0  center=auto delay=100+i time=700 condition=true',)])
            self.circle = xbmcgui.ControlImage(195+i, 511, 102, 103, "http://s6.postimg.org/u1jewuxzl/act_marco.png")
            self.addControl(self.circle)
            self.circle.setAnimations([('conditional','effect=zoom center=auto start=0 end=100 delay=5800 time=1500 tween=bounce condition=true ',),('WindowClose','effect=zoom end=0  center=auto delay=100+i time=700 condition=true',)])
            self.nombre_actor = xbmcgui.ControlFadeLabel(206+i, 605, 102, 60, self.fonts["12"])
            self.addControl(self.nombre_actor)
            self.nombre_actor.addLabel("[COLOR floralwhite][B]%s[/B][/COLOR]" % actor.get("name"))
            self.nombre_actor.setAnimations([('conditional','effect=fade start=0 end=100 delay=5800 time=1500 tween=bounce condition=true ',),('WindowClose','effect=fade end=0  center=auto time=700 condition=true',)])
            xbmc.sleep(200)
            i += 130
            sleep += 1000

        i = 0
        count = 0
        if self.item.contentType == "movie":
            reparto = self.infoLabels.get("crew", [])
        else:
            reparto = self.infoLabels.get("created_by", [])

        for crew in reparto:
            if crew.get('job', '') == 'Director' or self.item.contentType != "movie":
                if count == 2:
                    break
                count += 1
                image = "https://image.tmdb.org/t/p/original"
                if crew.get("profile_path"):
                    image += crew.get("profile_path", "")
                else:
                    image = "http://imgur.com/HGwvhMu.png"

                self.td = xbmcgui.ControlImage(880+i, 390, 63, 63, image)
                self.addControl(self.td)
                self.td.setAnimations([('conditional', 'effect=fade start=0% end=100%  delay=4200 time=200  condition=true',),('conditional','effect=slide start=-150,-60 delay=4200 time=450 condition=true tween=elastic',),('WindowClose','effect=slide end=-2000  center=auto time=700 condition=true',)])
                
                self.circle= xbmcgui.ControlImage(860+i, 372, 102, 103, "http://s6.postimg.org/u1jewuxzl/act_marco.png")
                self.addControl(self.circle)
                self.circle.setAnimations([('conditional', 'effect=fade start=0% end=100%  delay=4200 time=200  condition=true',),('conditional','effect=slide start=-200,-200 delay=4200 time=450 condition=true tween=elastic',),('WindowClose','effect=slide end=-2000  center=auto time=700 condition=true',)])
                self.nd = xbmcgui.ControlFadeLabel(860+i, 464, 105, 60, self.fonts["12"])
                self.addControl(self.nd)
                self.nd.addLabel("[COLOR floralwhite][B]%s[/B][/COLOR]" % crew["name"])
                self.nd.setAnimations([('conditional','effect=fade start=0 end=100 delay=4200 time=1500 tween=bounce condition=true',),('WindowClose','effect=slide end=2000  center=auto time=700 condition=true',)])
                i += 130

        try:
            if self.nd:
                self.img_dir = xbmcgui.ControlImage(740, 380, 100, 90, "http://s6.postimg.org/k8kl30pe9/director.png")
                self.addControl(self.img_dir)
                self.img_dir.setAnimations([('conditional','effect=fade start=0 end=100 delay=3200 time=700  condition=true ',),('WindowClose','effect=rotate end=-2000   time=700 condition=true',)])
        except:
            pass

        self.botones = []
        self.trailer_r = xbmcgui.ControlButton(790, 62, 55, 55, '', 'http://i.imgur.com/cGI2fxC.png', 'http://i.imgur.com/cGI2fxC.png')
        self.addControl(self.trailer_r)
        self.trailer_r.setAnimations([('conditional','effect=slide start=-2000 delay=4000 time=2500 condition=true',),('conditional','effect=rotate delay=4000 center=auto  start=0% end=360% time=2500  condition=true ',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',),('conditional','effect=rotate center=auto start=0% end=360% reversible=false  time=2000 loop=true condition=Control.HasFocus('+str(self.trailer_r.getId())+')'),('WindowClose','effect=slide end=2000 time=700 condition=true',)])
        self.botones.append(self.trailer_r)

        self.plusinfo = xbmcgui.ControlButton(1090, 20, 100, 100, '', 'http://i.imgur.com/1w5CFCL.png', 'http://i.imgur.com/1w5CFCL.png')
        self.addControl(self.plusinfo)
        self.plusinfo.setAnimations([('conditional','effect=slide start=0,-700 delay=5600 time=700 condition=true tween=elastic easing=out',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',),('conditional','effect=rotate center=auto start=0% end=360% reversible=false  time=2000 loop=true condition=Control.HasFocus('+str(self.plusinfo.getId())+')'),('WindowClose','effect=rotatey end=-300 time=1000 condition=true',)])
        self.botones.append(self.plusinfo)

        self.lupam = xbmcgui.ControlImage(950, 580, 60, 60, "http://imgur.com/VDdB0Uw.png")
        self.addControl(self.lupam)
        self.lupam.setAnimations([('conditional', 'effect=slide start=1500 delay=7020 time=200 tween=elastic condition=true',),('WindowClose','effect=zoom end=0 center=auto time=700 condition=true',)])

        self.focus = -1
        self.buscar = None
        canal = self.item.from_channel
        if not canal:
            canal = self.item.channel
        channel = __import__('channels.%s' % canal, None, None, ["channels.%s" % canal])
        if hasattr(channel, 'search'):
            if not self.item.thumb_busqueda:
                from core import channeltools
                self.item.thumb_busqueda = channeltools.get_channel_parameters(canal)["thumbnail"]
            self.buscar = xbmcgui.ControlButton(1040, 550, 150, 53, '', self.item.thumb_busqueda, self.item.thumb_busqueda)
            self.addControl(self.buscar)
            self.botones.append(self.buscar)
            self.buscar.setAnimations([('conditional', 'effect=slide start=0,700 delay=6000 time=200 condition=true',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',),('conditional','effect=zoom center=auto start=100% end=120% reversible=false tween=bounce time=1000 loop=true condition=Control.HasFocus('+str(self.buscar.getId())+')'),('WindowClose','effect=rotatey end=-300 time=1500 condition=true',)])
        self.global_search = xbmcgui.ControlButton(1046, 620, 140, 53, '', 'http://imgur.com/hoOvpHV.png', 'http://imgur.com/hoOvpHV.png')
        self.addControl(self.global_search)
        self.botones.append(self.global_search)
        self.global_search.setAnimations([('conditional', 'effect=slide start=0,700 delay=6090 time=200 condition=true',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',),('conditional','effect=zoom center=auto start=120% end=100% reversible=false tween=bounce time=1000 loop=true condition=Control.HasFocus('+str(self.global_search.getId())+')'),('WindowClose','effect=rotatey end=300 time=1500 condition=true',)])
        xbmc.sleep(200)


    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU or action == ACTION_GESTURE_SWIPE_LEFT or action == 110 or action == 92:
            global relatedWindow, exit_loop
            exit_loop = True
            self.close()

        if action == ACTION_MOVE_RIGHT or action == ACTION_MOVE_DOWN:
            if self.focus < len(self.botones)-1:
                self.focus += 1
                self.setFocus(self.botones[self.focus])

        if action == ACTION_MOVE_LEFT or action == ACTION_MOVE_UP:
            if self.focus > 0:
                self.focus -= 1
                self.setFocus(self.botones[self.focus])


    def onControl(self, control):
        global TrailerWindow, BusquedaWindow
        if control == self.plusinfo:
            global ActorInfoWindow, relatedWindow, ActoresWindow, imagesWindow, exit_loop, mainWindow
            exit_loop = True
            borrar = [relatedWindow, ActorInfoWindow, ActoresWindow, BusquedaWindow, TrailerWindow, imagesWindow]
            item_new = Item(channel=self.item.channel, contentType=self.item.contentType, infoLabels=self.infoLabels, thumb_busqueda=self.item.thumb_busqueda, from_channel=self.item.from_channel)
            for window in borrar:
                try:
                    window.close()
                    del window
                except:
                    pass
            mainWindow[-1].close()
            xbmc.sleep(200)
            start(item=item_new, from_window=True)
        elif control == self.trailer_r:
            item = self.item.clone(thumbnail=self.infoLabels.get("thumbnail"), contextual=True, contentTitle=self.infoLabels.get("title"), windowed=True, infoLabels=self.infoLabels)
            item.infoLabels["images"] = ""
            TrailerWindow = Trailer('TrailerWindow.xml', config.get_runtime_path()).Start(item, self.trailers)
        else:
            if control == self.buscar:
                try:
                    check_busqueda = "no_global"
                    canal = self.item.from_channel
                    if not canal:
                        canal = self.item.channel
                    channel = __import__('channels.%s' % canal, None, None, ["channels.%s" % canal])
                    itemlist = channel.search(self.item.clone(), self.infoLabels.get("title"))
                    if not itemlist and self.infoLabels.get("originaltitle"):
                        itemlist = channel.search(self.item.clone(), self.infoLabels.get("originaltitle", ""))
                except:
                    import traceback
                    logger.info(traceback.format_exc())

            elif control == self.global_search:
                check_busqueda = "global"
                itemlist = busqueda_global(self.item, self.infoLabels)
                if len(itemlist) == 1 and self.infoLabels.get("originaltitle"):
                    itemlist = busqueda_global(self.item, self.infoLabels, org_title=True)

            if itemlist:
                BusquedaWindow = Busqueda('DialogSelect.xml', config.get_runtime_path(), itemlist=itemlist, item=self.item)
                BusquedaWindow.doModal()
            else:
                if check_busqueda == "no_global":
                    self.removeControl(self.buscar)
                    self.notfound = xbmcgui.ControlImage(800, 520, 300, 120, "http://imgur.com/V1xs9pT.png")
                    self.addControl(self.notfound)
                    self.notfound.setAnimations([('conditional', 'effect=zoom center=auto start=500% end=0% time=2000 condition=true',)])
                else:
                    self.removeControl(self.global_search)
                    self.notfound = xbmcgui.ControlImage(800, 520, 300, 120, "http://imgur.com/V1xs9pT.png")
                    self.addControl(self.notfound)
                    self.notfound.setAnimations([('conditional', 'effect=zoom center=auto start=500% end=0% time=2000 condition=true',)])


def busqueda_global(item, infoLabels, org_title=False):
    logger.info("pelisalacarta.channels.buscador search")
    if item.contentType != "movie":
        cat = ["serie"]
    else:
        cat = ["movie"]

    new_item = Item()
    new_item.extra = infoLabels.get("title", "")
    new_item.extra = re.sub('\[.*?\]', '', new_item.extra)

    if org_title:
        new_item.extra = infoLabels.get("originaltitle", "")
    new_item.category = item.contentType

    from channels import buscador
    return buscador.do_search(new_item, cat)


class Busqueda(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.lista = kwargs.get("itemlist")
        self.item = kwargs.get("item")


    def onInit(self):
        try:
            self.control_list = self.getControl(6)
            self.getControl(5).setNavigation(self.control_list, self.control_list, self.control_list, self.control_list)
            self.getControl(3).setEnabled(0)
            self.getControl(3).setVisible(0)
        except:
            pass
        if self.item.contentType != "movie":
            self.getControl(1).setLabel("[COLOR orange][B]¿Está la serie que buscas?[/B][/COLOR]")
        else:
            self.getControl(1).setLabel("[COLOR orange][B]¿Está la película que buscas?[/B][/COLOR]")

        self.getControl(5).setLabel("[COLOR tomato][B]Cerrar[/B][/COLOR]")
        self.control_list.reset()
        items = []
        for item_l in self.lista:
            item = xbmcgui.ListItem(item_l.title)
            try:
                item.setArt({"thumb": item_l.thumbnail})
            except:
                item.setThumbnailImage(item_l.thumbnail)
            item.setProperty("item_copy", item_l.tourl())
            items.append(item)

        self.getControl(6).addItems(items)
        self.setFocusId(6)


    def onAction(self, action):   
        global BusquedaWindow    
        if (action == ACTION_SELECT_ITEM or action == 100) and self.getFocusId() == 6:
            dialog = platformtools.dialog_progress_bg("Cargando resultados", "Espere........")
            selectitem = self.getControl(6).getSelectedItem()
            item = Item().fromurl(selectitem.getProperty("item_copy"))
            exec "import channels."+item.channel+" as channel"
            itemlist = getattr(channel, item.action)(item)
            global SearchWindows
            window = GlobalSearch('DialogSelect.xml', config.get_runtime_path(), itemlist=itemlist, dialog=dialog)
            SearchWindows.append(window)
            self.close()
            window.doModal()

        if (action == ACTION_SELECT_ITEM or action == 100) and self.getFocusId() == 5:
            self.close()

        elif action == ACTION_PREVIOUS_MENU or action == ACTION_GESTURE_SWIPE_LEFT or action == 110 or action == 92:
            self.close()


class GlobalSearch(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.lista = kwargs.get("itemlist")
        self.dialog = kwargs.get("dialog")


    def onInit(self):
        self.dialog.close()
        try:
            self.control_list = self.getControl(6)
            self.getControl(5).setNavigation(self.control_list, self.control_list, self.control_list, self.control_list)
            self.getControl(3).setEnabled(0)
            self.getControl(3).setVisible(0)
        except:
            pass

        self.getControl(1).setLabel("[COLOR orange][B]Selecciona...[/B][/COLOR]")
        self.getControl(5).setLabel("[COLOR tomato][B]Cerrar[/B][/COLOR]")
        self.control_list.reset()
        if not self.lista:
            global SearchWindows
            self.close()
            SearchWindows.pop()
            if len(SearchWindows) - 1 >= 0:
                SearchWindows[-1].doModal()
            else:
                BusquedaWindow.doModal()
        else:
            items = []
            for item_l in self.lista:
                item = xbmcgui.ListItem(item_l.title)
                try:
                    item.setArt({"thumb": item_l.thumbnail})
                except:
                    item.setThumbnailImage(item_l.thumbnail)
                item.setProperty("item_copy", item_l.tourl())
                items.append(item)
            self.getControl(6).addItems(items)
            self.setFocusId(6)


    def onAction(self, action):
        global SearchWindows
        if (action == ACTION_SELECT_ITEM or action == 100) and self.getFocusId() == 6:
            selectitem = self.getControl(6).getSelectedItem()
            item = Item().fromurl(selectitem.getProperty("item_copy"))
            exec "import channels."+item.channel+" as channel"
            ventana_error = None
            if item.action == "play":
                if hasattr(channel, 'play'):
                    itemlist = channel.play(item)
                    if len(itemlist) > 0 :
                        item = itemlist[0]
                    else:
                        ventana_error = xbmcgui.Dialog()
                        ok = ventana_error.ok("plugin", "No hay nada para reproducir")
                        return

                global BusquedaWindow, exit_loop, mainWindow, ActorInfoWindow, relatedWindow, ActoresWindow
                borrar = [relatedWindow, ActorInfoWindow, ActoresWindow, BusquedaWindow]

                borrar.extend(SearchWindows)
                borrar.extend(mainWindow)
                if item.server != "torrent":
                    import time
                    recuperar = False
                    inicio = time.time()
                    try:
                        retorna = platformtools.play_video(item)
                    except:
                        retorna = True
                    xbmc.sleep(1500)
                    if not retorna and xbmc.Player().isPlaying():
                        exit_loop = True
                        for window in borrar:
                            try:
                                window.close()
                            except:
                                pass
                        while True:
                            xbmc.sleep(1000)
                            if not xbmc.Player().isPlaying():
                                break
                            if time.time() - inicio > 120:
                                return

                        for window in SearchWindows:
                            window.doModal()
                        BusquedaWindow.doModal()
                        mainWindow[-1].doModal()

                elif item.server == "torrent":
                    exit_loop = True
                    for window in borrar:
                        try:
                            window.close()
                            del window
                        except:
                            pass
                    platformtools.play_video(item)

            else:
                try:
                    dialog = platformtools.dialog_progress_bg("Cargando resultados", "Espere........")
                    itemlist = getattr(channel, item.action)(item)
                    window = GlobalSearch('DialogSelect.xml', config.get_runtime_path(), itemlist=itemlist, dialog=dialog)
                    SearchWindows.append(window)
                    self.close()
                    window.doModal()
                except:
                    pass

        elif (action == ACTION_SELECT_ITEM or action == 100) and self.getFocusId() == 5:
            self.close()
            SearchWindows.pop()
            if len(SearchWindows) - 1 >= 0:
                SearchWindows[-1].doModal()
            else:
                BusquedaWindow.doModal()

        elif action == ACTION_PREVIOUS_MENU or action == ACTION_GESTURE_SWIPE_LEFT or action == 110 or action == 92:
            self.close()
            SearchWindows.pop()
            if len(SearchWindows) - 1 >= 0:
                SearchWindows[-1].doModal()
            else:
                BusquedaWindow.doModal()


class Actores(xbmcgui.WindowXMLDialog):
    def __init__(self, *args, **kwargs):
        self.tmdb_id = kwargs.get("tmdb_id")
        self.item = kwargs.get("item")
        self.fonts = kwargs.get("fonts")


    def onInit(self):
        try:
           self.control_list = self.getControl(6)
           self.getControl(5).setNavigation(self.control_list, self.control_list, self.control_list, self.control_list)
           self.getControl(3).setEnabled(0)
           self.getControl(3).setVisible(0)
        except:
           pass
        self.getControl(1).setLabel("[COLOR orange][B]Reparto[/B][/COLOR]")
        self.getControl(5).setLabel("[COLOR red][B]Cerrar[/B][/COLOR]")
        self.control_list.reset()
        items = []

        tipo = self.item.contentType
        if tipo != "movie":
            tipo = "tv"
        otmdb = tmdb.Tmdb(id_Tmdb=self.tmdb_id, tipo=tipo)
        actores = otmdb.result.get("credits", {}).get("cast", [])

        if self.item.contentType == "movie":
            reparto = otmdb.result.get("credits", {}).get("crew", [])
        else:
            reparto = otmdb.result.get("created_by", [])

        for crew in reparto:
            if crew.get('job', '') == 'Director' or self.item.contentType != "movie":
                actores.insert(0, crew)

        for actor in actores:
            name_info = "[COLOR yellow][B]%s[/B][/COLOR]" % actor["name"]
            try:
                name = "[COLOR salmon]%s[/COLOR]  [COLOR papayawhip](%s)[/COLOR]" % (actor["name"], actor["character"])
                job = "actor"
            except:
                job = "Director"
                name = "[COLOR salmon]%s[/COLOR]  [COLOR gold](%s)[/COLOR]" % (actor["name"], job)
            image = "https://image.tmdb.org/t/p/original"
            if actor["profile_path"]:
                image += actor["profile_path"]
            else:
                image = "http://i.imgur.com/dvMKE1V.jpg"
            item = xbmcgui.ListItem(name)
            try:
                item.setArt({"thumb":image})
            except:
                item.setThumbnailImage(image)
            item.setProperty("id_actor", str(actor["id"]))
            item.setProperty("name_info", name_info)
            item.setProperty("thumbnail", image)
            item.setProperty("job", job)
            items.append(item)

        self.getControl(6).addItems(items)
        self.setFocusId(6)


    def onAction(self, action):
        if (action == ACTION_SELECT_ITEM or action == 100) and self.getFocusId() == 6:
            selectitem = self.getControl(6).getSelectedItem()
            id_actor = selectitem.getProperty("id_actor")
            name_info = selectitem.getProperty("name_info")
            thumbnail = selectitem.getProperty("thumbnail")
            job = selectitem.getProperty("job")
            dialog = platformtools.dialog_progress("[COLOR darkturquoise][B]Cargando nuevos datos[/B][/COLOR]", "[COLOR yellow]Obteniendo datos del %s...[/COLOR]" % job.lower())

            global ActorInfoWindow
            ActorInfoWindow = ActorInfo(id=id_actor, name=name_info, thumbnail=thumbnail, item=self.item, fonts=self.fonts, dialog=dialog, job=job)
            ActorInfoWindow.doModal()
            xbmc.sleep(400)
        elif (action == ACTION_SELECT_ITEM or action == 100) and self.getFocusId() == 5:
            self.close()

        elif action == ACTION_PREVIOUS_MENU or action == ACTION_GESTURE_SWIPE_LEFT or action == 110 or action == 92:
            self.close()


class ActorInfo(xbmcgui.WindowDialog):
    def __init__(self, *args, **kwargs):
        global exit_loop
        if exit_loop:
            exit_loop = False
        self.id = kwargs.get('id')
        self.nombre = kwargs.get('name')
        self.thumbnail = kwargs.get('thumbnail')
        self.item = kwargs.get('item')
        self.fonts = kwargs.get('fonts')
        self.job = kwargs.get('job')

        self.dialog = kwargs.get('dialog')
        if self.item.contentType == "movie":
            tipo = "movie"
            search = {'url': 'person/%s' % self.id, 'language': 'es', 'append_to_response': 'movie_credits,images'}
        else:
            tipo = "tv"
            search = {'url': 'person/%s' % self.id, 'language': 'es', 'append_to_response': 'tv_credits,images'}

        actor_tmdb = tmdb.Tmdb(discover=search)
        if not actor_tmdb.result.get("biography") and actor_tmdb.result.get("imdb_id"):
            data = scrapertools.downloadpage("http://www.imdb.com/name/%s/bio" % actor_tmdb.result["imdb_id"])
            info = scrapertools.find_single_match(data, '<div class="soda odd">.*?<p>(.*?)</p>')
            if info:
                bio = dhe(scrapertools.htmlclean(info.strip()))
                try:
                    info_list = []
                    while bio:
                        info_list.append(bio[:1900])
                        bio = bio[1900:]
                    bio = []
                    threads = {}
                    for i, info_ in enumerate(info_list):
                        t = Thread(target=translate,args=[info_, "es", "en", i, bio])
                        t.setDaemon(True)
                        t.start()
                        threads[i] = t

                    while threads:
                        for key, t in threads.items():
                            if not t.isAlive():
                                threads.pop(key)
                        xbmc.sleep(100)
                    if bio:
                        bio.sort(key=lambda x:x[0])
                        biography = ""
                        for i, b in bio:
                            biography += b
                        actor_tmdb.result["biography"] = dhe(biography)
                    else:
                        bio = dhe(scrapertools.htmlclean(info.strip()))
                        actor_tmdb.result["biography"] = dhe(bio)
                except:
                    bio = dhe(scrapertools.htmlclean(info.strip()))
                    actor_tmdb.result["biography"] = bio
            else:
                actor_tmdb.result["biography"] = "Sin información"
        elif not actor_tmdb.result.get("biography"):
            actor_tmdb.result["biography"] = "Sin información"

        self.setCoordinateResolution(2)
        self.background = xbmcgui.ControlImage(30, -5, 1250, 730, 'http://imgur.com/7ccBX3g.png')
        self.addControl(self.background)
        self.background.setAnimations([('conditional', 'effect=fade start=0% end=100% delay=2000 time=1500 condition=true',),('WindowClose','effect=slide end=0,-700% time=1000 condition=true',)])
        self.filmo = xbmcgui.ControlImage(330, 470, 230, 45, 'http://s6.postimg.org/rlktamqhd/filmography1.png')
        self.addControl(self.filmo)
        self.filmo.setAnimations([('conditional', 'effect=zoom start=0,700 end=100% center=auto delay=5500 time=1000 condition=true tween=elastic',),('WindowClose','effect=zoom start=100% end=0% time=1000 condition=true',)])

        self.title = xbmcgui.ControlTextBox(470, 30, 730, 250)
        self.addControl(self.title)
        self.title.setAnimations([('conditional', 'effect=slide start=-1500% end=0% delay=3000 time=1500 condition=true',),('WindowClose','effect=slide end=1500% time=1000 condition=true',)])
        self.title.setText(self.nombre)
        self.info_actor = xbmcgui.ControlTextBox(470, 70, 750, 400)
        self.addControl(self.info_actor)
        self.info_actor.setAnimations([('conditional', 'effect=slide start=2000% end=-10% delay=5300 time=1500 tween=bounce condition=true',),('WindowClose','effect=slide end=-2000% time=1000 condition=true',)])
        try:
            self.info_actor.autoScroll(7000, 6000, 30000)
        except:
            xbmc.executebuiltin('Notification([COLOR red][B]Actualiza Kodi a su última versión[/B][/COLOR], [COLOR skyblue]para mejor info[/COLOR],8000, "http://i.imgur.com/mHgwcn3.png")')
        self.info_actor.setText("[COLOR coral][B]%s[/B][/COLOR]" % actor_tmdb.result.get("biography", "Sin información"))

        self.titulos = []
        tipo_busqueda = "cast"
        if self.job != "actor":
            tipo_busqueda = "crew"
        ids = []
        for entradas in actor_tmdb.result.get("%s_credits" % tipo, {}).get(tipo_busqueda, []):
            if entradas["id"] in ids:
                continue
            else:
                ids.append(entradas["id"])
            thumb = "https://image.tmdb.org/t/p/original"
            if entradas["poster_path"]:
                thumb += entradas["poster_path"]
            else:
                thumb = "http://s6.postimg.org/tw1vhymj5/noposter.png"
            if self.item.contentType == "movie":
                self.titulos.append([entradas["id"], entradas.get("title", entradas.get("original_title", "")), thumb])
            else:
                self.titulos.append([entradas["id"], entradas.get("title", entradas.get("original_title", "")), thumb])

        self.dialog.update(40, '[COLOR rosybrown]Obteniendo filmografía...[/COLOR]')
        self.mas_pelis = 8
        self.idps = []
        self.botones = []
        self.botones_maspelis = []
        self.focus = -1
        i = 0
        count = 0
        self.btn_left = xbmcgui.ControlButton(90, 490, 70, 29, '', "http://s6.postimg.org/i3pnobu6p/redarrow.png", "http://s6.postimg.org/i3pnobu6p/redarrow.png")
        self.addControl(self.btn_left)
        self.btn_left.setAnimations([('conditional','effect=zoom start=720,642,70,29 end=640,642,69,29 time=1000 loop=true tween=bounce condition=Control.HasFocus('+str(self.btn_left.getId())+')',),('WindowClose','effect=fade end=0% time=1000 condition=true',)])
        self.btn_left.setVisible(False)
        self.botones.append(self.btn_left)
        for idp, peli, foto in self.titulos:
            if count % 8 == 0:
               i = 0
            self.image = xbmcgui.ControlButton(65+i, 538, 135, 160, '', foto, foto)
            self.neon = xbmcgui.ControlImage(60+i, 525, 145, 186, "http://s6.postimg.org/x0jspnxch/buttons.png")
            fadelabel = xbmcgui.ControlFadeLabel(67+i, 698, 135, 50)
            self.botones.append(self.image)

            if count < 8:
                self.addControl(self.image)
                self.image.setAnimations([('conditional', 'effect=rotatey start=200 end=0 delay=2000 time=900 tween=elastic condition=true',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',), ('focus', 'effect=rotate center=auto start=0% end=360% time=650 tween=bounce',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',),])
                self.addControl(self.neon)
                self.neon.setVisibleCondition('[Control.HasFocus('+str(self.image.getId())+')]')
                self.neon.setAnimations([('conditional', 'effect=rotate center=auto start=0% end=360% time=650 tween=bounce condition=Control.HasFocus('+str(self.image.getId())+')',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',),])

                self.addControl(fadelabel)
                fadelabel.addLabel(peli)
                fadelabel.setAnimations([('conditional', 'effect=rotatey start=200 end=0 delay=6200 time=900 tween=elastic condition=true',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])

            self.idps.append([self.image, peli, idp, foto])
            self.botones_maspelis.append([self.image, self.neon, fadelabel, peli])

            i += 150
            count += 1
        xbmc.sleep(200)
        if len(self.titulos) > 8:
            self.btn_right = xbmcgui.ControlButton(1150, 495, 60, 27, '', "http://s6.postimg.org/j4uhr70k1/greenarrow.png", "http://s6.postimg.org/j4uhr70k1/greenarrow.png")
            self.addControl(self.btn_right)
            self.btn_right.setAnimations([('conditional','effect=slide start=-3000 end=0 delay=5000 time=2000 condition=true tween=bounce',),('conditional','effect=zoom start=230,490, 60, 27, 29 end=1230,642,61,27 time=1000 loop=true tween=bounce condition=Control.HasFocus('+str(self.btn_right.getId())+')',),('WindowClose','effect=fade end=0% time=1000 condition=true',)])
            self.botones.append(self.btn_right)

        xbmc.sleep(200)
        self.dialog.update(80, '[COLOR plum]Recopilando imágenes...[/COLOR]')
        self.images = []
        for images in actor_tmdb.result.get("images", {}).get("profiles", []):
            imagen = "https://image.tmdb.org/t/p/original" + images["file_path"]
            self.images.append(imagen)

        if len(self.images) <= 1 or (len(self.images) == 2 and self.images[0] == self.images[1]):
            self.marco = xbmcgui.ControlImage(100, 23, 330, 425, 'http://s6.postimg.org/nkmk7b8nl/marco_foto2_copia.png')
            self.addControl(self.marco)
            self.marco.setAnimations([('conditional', 'effect=rotatey start=100% end=0% delay=2400 time=1500 condition=true',),('WindowClose','effect=fade end=0% time=1000 condition=true',)])
            self.thumb = xbmcgui.ControlImage(115, 40, 294, 397, self.thumbnail)
            self.addControl(self.thumb)
            self.thumb.setAnimations([('conditional', 'effect=rotatey start=100% end=0% delay=2380 time=1500 condition=true',),('WindowClose','effect=fade end=0% time=1000 condition=true',)])
            xbmc.sleep(300)
        else:
            self.start_change = False
            self.th = Thread(target=self.change_image)
            self.th.setDaemon(True)
            self.th.start()

        self.dialog.close()

    def change_image(self):
        global exit_loop
        imagenes = []
        while True:
            xbmc.sleep(100)
            for i, image in enumerate(self.images):
                xbmc.sleep(400)
                if i == 0:
                    xbmc.sleep(300)
                    self.marco = xbmcgui.ControlImage(100, 23, 330, 425, 'http://s6.postimg.org/nkmk7b8nl/marco_foto2_copia.png')
                    self.thumb = xbmcgui.ControlImage(115, 40, 294, 397, "")
                    xbmc.sleep(500)
                    self.addControl(self.marco)
                    self.marco.setAnimations([('conditional', 'effect=rotatey start=100% end=0% delay=2300 time=1500 condition=true',),('WindowClose','effect=fade end=0% time=1000 condition=true',)])
                    self.addControl(self.thumb)
                    self.thumb.setImage(self.thumbnail)
                    self.thumb.setAnimations([('conditional', 'effect=rotatey start=100% end=0% delay=2280 time=1500 condition=true',),('WindowClose','effect=fade end=0% time=1000 condition=true',)])
                    xbmc.sleep(4000)
                    for img in imagenes:
                        self.removeControls([img[0], img[1]])
                    imagenes = []
                    imagenes.append([self.thumb, self.marco])
                    if exit_loop:
                        break

                if exit_loop:
                    break
                if i > 0:
                    if exit_loop:
                        break
                    xbmc.sleep(5200)
                    self.marco = xbmcgui.ControlImage(100, 23, 330, 425, 'http://s6.postimg.org/4syg4krkh/marco_foto.png')
                    self.addControl(self.marco)
                    self.marco.setAnimations([('conditional', 'effect=rotatey start=100% end=0% delay=300 time=1500 condition=true',),('WindowClose','effect=fade end=0% time=1000 condition=true',)])
                    self.thumb = xbmcgui.ControlImage(115, 40, 294, 397, "")
                    self.addControl(self.thumb)
                    self.thumb.setImage(image, True)
                    self.thumb.setAnimations([('conditional', 'effect=rotatey start=100% end=0% delay=285 time=1500 condition=true',),('WindowClose','effect=fade end=0% time=1000 condition=true',)])
                    imagenes.append([self.thumb, self.marco])

                    xbmc.sleep(400)
            if exit_loop:
                break
        logger.info("salimos carajo xD")


    def onAction(self, action):
        global exit_loop
        if exit_loop:
            exit_loop = False

        if action == ACTION_MOVE_RIGHT or action == ACTION_MOVE_DOWN :
           if self.focus < len(self.botones)-1:
                self.focus += 1
                while True:
                    id_focus = str(self.botones[self.focus].getId())
                    if xbmc.getCondVisibility('[Control.IsVisible('+id_focus+')]'):
                        self.setFocus(self.botones[self.focus])
                        break
                    self.focus += 1
                    if self.focus == len(self.botones):
                        break

        if action == ACTION_MOVE_LEFT or action == ACTION_MOVE_UP :
            if self.focus > 0:
                self.focus -= 1
                while True:
                    id_focus = str(self.botones[self.focus].getId())
                    if xbmc.getCondVisibility('[Control.IsVisible('+id_focus+')]'):
                        self.setFocus(self.botones[self.focus])
                        break
                    self.focus -= 1
                    if self.focus == len(self.botones):
                        break

        if action == ACTION_PREVIOUS_MENU or action == ACTION_GESTURE_SWIPE_LEFT or action == 110 or action == 92:
            exit_loop = True
            self.close()

        if action == 105 or action == 6:
            for boton, peli, id, poster2 in self.idps:
                try:
                    if self.getFocusId() == boton.getId() and self.btn_right:
                        self.focus = len(self.botones) - 1
                        xbmc.executebuiltin('SendClick(%s)' % self.btn_right.getId())
                except:
                    pass

        if action == 104 or action == 5:
            for boton, peli, id, poster2 in self.idps:
                try:
                    if self.getFocusId() == boton.getId() and self.btn_left:
                        self.setFocus(self.btn_left)
                        xbmc.executebuiltin('SendClick(%s)' % self.btn_left.getId())
                except:
                    pass


    def onControl(self, control):
        try:
            if control == self.btn_right:
                i = 1
                count = 0
                for afoto, neon, fadelabel, peli in self.botones_maspelis:
                    if i > self.mas_pelis - 8 and i <= self.mas_pelis and count < 8:
                        self.removeControls([afoto, neon, fadelabel])
                        count += 1
                    elif i > self.mas_pelis and count < 16:
                        self.addControl(afoto)
                        afoto.setAnimations([('conditional', 'effect=rotatey start=200 end=0 time=900 delay=200 tween=elastic condition=true',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',), ('focus', 'effect=rotate center=auto start=0% end=360% time=650 tween=bounce',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',),])
                        self.addControl(neon)
                        neon.setVisibleCondition('[Control.HasFocus('+str(afoto.getId())+')]')
                        neon.setAnimations([('conditional', 'effect=rotate center=auto start=0% end=360% time=650 tween=bounce condition=Control.HasFocus('+str(afoto.getId())+')',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',),])
                        self.addControl(fadelabel)
                        fadelabel.addLabel(peli)
                        fadelabel.setAnimations([('conditional', 'effect=rotatey start=200 end=0 time=900 tween=elastic condition=true',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])

                        count += 1
                        self.mas_pelis += 1
                        xbmc.sleep(120)
                    i += 1

                if self.mas_pelis > 8 and self.mas_pelis < 17:
                    self.btn_left.setVisible(True)

                if len(self.botones_maspelis) < self.mas_pelis + 1:
                    self.btn_right.setVisible(False)
                    self.btn_right.setVisible(False)
                    self.setFocus(self.btn_left)
                    self.focus = 4
                else:
                    self.focus = len(self.botones) - 1
                    self.setFocus(self.btn_right)

                xbmc.sleep(300)
        except:
            pass
        try:
            if control == self.btn_left:
                i = 1
                count = 0
                if self.mas_pelis == len(self.botones_maspelis):
                    self.btn_right.setVisible(True)
                len_pelis = self.mas_pelis
                for afoto, neon, fadelabel, peli in self.botones_maspelis:
                    resta = 8 + (len_pelis%8)
                    if resta == 8:
                        resta = 16
                    resta2 = len_pelis%8
                    if not resta2:
                        resta2 = 8
                    if i > len_pelis - resta and count < 8:
                        self.addControl(afoto)
                        afoto.setAnimations([('conditional', 'effect=rotatey start=200 end=0 time=900 tween=elastic condition=true',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',), ('focus', 'effect=rotate center=auto start=0% end=360% time=650 tween=bounce',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',),])
                        self.addControl(neon)
                        neon.setVisibleCondition('[Control.HasFocus('+str(afoto.getId())+')]')
                        neon.setAnimations([('conditional', 'effect=rotate center=auto start=0% end=360% time=650 tween=bounce condition=Control.HasFocus('+str(afoto.getId())+')',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',),])
                        self.addControl(fadelabel)
                        fadelabel.addLabel(peli)
                        fadelabel.setAnimations([('conditional', 'effect=rotatey start=200 end=0 time=900 tween=elastic condition=true',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])
                        count += 1
                    elif i > len_pelis - resta2 and i <= len_pelis and count < 16:
                        self.removeControls([afoto, neon, fadelabel])
                        count += 1
                        self.mas_pelis -= 1
                    i += 1

                if self.mas_pelis == 8:
                    self.btn_left.setVisible(False)
        except:
            pass

        for boton, peli, id, poster2 in self.idps:
            if control == boton:
                tipo = self.item.contentType
                if tipo != "movie":
                    tipo = "tv"
                new_tmdb = tmdb.Tmdb(id_Tmdb=id, tipo=tipo)
                new_infolabels = new_tmdb.get_infoLabels()

                new_infolabels["cast"] = new_tmdb.result.get("credits_cast", [])
                new_infolabels["crew"] = new_tmdb.result.get("credits_crew", [])
                new_infolabels["created_by"] = new_tmdb.result.get("created_by", [])
                global relatedWindow
                relatedWindow = related(item=self.item, infolabels=new_infolabels, fonts=self.fonts)
                relatedWindow.doModal()


class images(xbmcgui.WindowDialog):
    def __init__(self, *args, **kwargs):
        self.fanartv = kwargs.get("fanartv", {})
        self.tmdb = kwargs.get("tmdb", {})
        self.imdb = kwargs.get("imdb", [])
        self.fa = kwargs.get("fa", [])
        self.mal = kwargs.get("mal", [])

        self.imagenes = []
        for key, value in self.tmdb.iteritems():
            for detail in value:
                self.imagenes.append('http://image.tmdb.org/t/p/w342' + detail["file_path"])
        for tipo, child in self.fanartv.iteritems():
            for imagen in child:
                self.imagenes.append(imagen["url"].replace("/fanart/", "/preview/"))
        for imagen, title in self.fa:
            self.imagenes.append(imagen)
        for imagen in self.imdb:
            self.imagenes.append(imagen["src"])
        for imagen, title in self.mal:
            self.imagenes.append(imagen)

        self.setCoordinateResolution(2)
        self.shadow = xbmcgui.ControlImage(145, 10, 1011, 700, 'http://imgur.com/66VSLTo.png')
        self.addControl(self.shadow)
        self.shadow.setAnimations([('conditional', 'effect=slide start=1000% end=100% delay=672 time=2500 condition=true',),('WindowClose','effect=slide end=0,-700% time=1000 condition=true',)])
        imagen_inicial = self.imagenes[0].replace("/preview/", "/fanart/").replace("-s200", "-large").replace("/w342/", "/original/")
        self.background = xbmcgui.ControlImage(148, 17, 1003, 560, imagen_inicial, 2)
        self.addControl(self.background)
        self.background.setAnimations([('conditional', 'effect=slide start=1000% end=100% delay=670 time=2500 condition=true',),('WindowClose','effect=slide end=0,-700% time=1000 condition=true',)])

        self.botones = []
        self.imgcount = 8
        self.urls = []
        self.botones_imgs = []
        self.focus = -1
        i = 0
        count = 0
        self.btn_left = xbmcgui.ControlButton(293, 550, 70, 29, '', "http://s6.postimg.org/i3pnobu6p/redarrow.png", "http://s6.postimg.org/i3pnobu6p/redarrow.png")
        self.addControl(self.btn_left)
        self.btn_left.setAnimations([('conditional','effect=zoom start=-100 end=100 delay=5000 time=2000 condition=true tween=bounce' ,),('conditional','effect=zoom start=293,642,70,29 end=243,642,69,29 time=1000 loop=true tween=bounce condition=Control.HasFocus('+str(self.btn_left.getId())+')',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])
        self.btn_left.setVisible(False)
        self.botones.append(self.btn_left)
        for img in self.imagenes:
            img = img.replace(" ", "%20")
            if count % 8 == 0:
                i = 0
            self.image = xbmcgui.ControlButton(280+i, 590, 100, 98, '', img, img)
            self.neon = xbmcgui.ControlImage(280+i, 590, 100, 98, "http://s6.postimg.org/x0jspnxch/buttons.png")
            self.botones.append(self.image)
            if count < 8:
                self.addControl(self.image)
                self.image.setAnimations([('conditional', 'effect=rotatey start=200 end=0  delay=3500 time=900 tween=elastic condition=true',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])
                self.addControl(self.neon)
                self.neon.setVisibleCondition('[Control.HasFocus('+str(self.image.getId())+')]')
                self.neon.setAnimations([('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])

            self.urls.append([self.image, img])
            self.botones_imgs.append([self.image, self.neon])

            i += 120
            count += 1
        xbmc.sleep(200)
        if len(self.imagenes) > 8:
            self.btn_right = xbmcgui.ControlButton(1150, 550, 60, 27, '', "http://s6.postimg.org/j4uhr70k1/greenarrow.png", "http://s6.postimg.org/j4uhr70k1/greenarrow.png")
            self.addControl(self.btn_right)
            self.btn_right.setAnimations([('conditional','effect=slide start=-3000 end=0 delay=3600 time=2000 condition=true tween=bounce' ,),('conditional','effect=zoom start=230,490, 60, 27, 29 end=1190,642,61,27 time=1000 loop=true tween=bounce condition=Control.HasFocus('+str(self.btn_right.getId())+')',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])
            self.botones.append(self.btn_right)
        xbmc.sleep(200)

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU or action == ACTION_GESTURE_SWIPE_LEFT or action == 110 or action == 92:
            self.close()

        if action == ACTION_MOVE_RIGHT or action == ACTION_MOVE_DOWN:
            if self.focus < len(self.botones)-1:
                self.focus += 1
                while True:
                    id_focus = str(self.botones[self.focus].getId())
                    if xbmc.getCondVisibility('[Control.IsVisible('+id_focus+')]'):
                        self.setFocus(self.botones[self.focus])
                        break
                    self.focus += 1
                    if self.focus == len(self.botones):
                        break

        if action == ACTION_MOVE_LEFT or action == ACTION_MOVE_UP:
            if self.focus > 0:
                self.focus -= 1
                while True:
                    id_focus = str(self.botones[self.focus].getId())
                    if xbmc.getCondVisibility('[Control.IsVisible('+id_focus+')]'):
                        self.setFocus(self.botones[self.focus])
                        break
                    self.focus -= 1
                    if self.focus == len(self.botones):
                        break

        if action == 105 or action == 6:
            for image, neon in self.botones_imgs:
                try:
                    if self.getFocusId() == image.getId() and self.btn_right:
                        self.focus = len(self.botones) - 1
                        xbmc.executebuiltin('SendClick(%s)' % self.btn_right.getId())
                except:
                    pass

        if action == 104 or action == 5:
            for image, neon in self.botones_imgs:
                try:
                    if self.getFocusId() == image.getId() and self.btn_left:
                        self.focus = 0
                        xbmc.executebuiltin('SendClick(%s)' % self.btn_left.getId())
                except:
                    pass


    def onControl(self, control):
        try:
            if control == self.btn_right:
                i = 1
                count = 0
                for image, neon in self.botones_imgs:
                    if i > self.imgcount - 8 and i <= self.imgcount and count < 8:
                        self.removeControls([image, neon])
                        count += 1
                    elif i > self.imgcount and count < 16:
                        self.addControl(image)
                        image.setAnimations([('conditional', 'effect=rotatey start=200 end=0 delay=600 time=900 tween=elastic condition=true',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])
                        self.addControl(neon)
                        neon.setVisibleCondition('[Control.HasFocus('+str(image.getId())+')]')
                        neon.setAnimations([('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])

                        count += 1
                        self.imgcount += 1
                        xbmc.sleep(120)
                    i += 1

                if self.imgcount > 8 and self.imgcount < 17:
                    self.btn_left.setVisible(True)

                if len(self.botones_imgs) < self.imgcount + 1:
                    self.btn_right.setVisible(False)

                self.focus = -1
                xbmc.executebuiltin('Action(Right)')
                xbmc.sleep(300)
        except:
            pass

        try:
            if control == self.btn_left:
                i = 1
                count = 0
                if self.imgcount == len(self.botones_imgs):
                    self.btn_right.setVisible(True)

                len_images = self.imgcount
                for image, neon in self.botones_imgs:
                    resta = 8 + (len_images % 8)
                    if resta == 8:
                        resta = 16
                    resta2 = len_images % 8
                    if not resta2:
                        resta2 = 8
                    if i > len_images - resta and count < 8:
                        self.addControl(image)
                        image.setAnimations([('conditional', 'effect=rotatey start=200 end=0  delay=600 time=900 tween=elastic condition=true',),('unfocus', 'effect=zoom center=auto start=70% end=100% time=700 reversible=false',),('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])
                        self.addControl(neon)
                        neon.setVisibleCondition('[Control.HasFocus('+str(image.getId())+')]')
                        neon.setAnimations([('WindowClose','effect=slide end=0,700% time=1000 condition=true',)])
                        count += 1
                    elif i > len_images - resta2 and i <= len_images and count < 16:
                        self.removeControls([image, neon])
                        count += 1
                        self.imgcount -= 1
                    i += 1

                if self.imgcount == 8:
                    self.btn_left.setVisible(False)
                    self.setFocus(self.botones[1])
                else:
                    self.setFocus(self.btn_left)
        except:
            pass

        for boton, url in self.urls:
            if control == boton:
                if "fanart.tv" in url:
                    url = url.replace("/preview/", "/fanart/")
                elif "filmaffinity" in url:
                    url = url.replace("-s200", "-large")
                elif "image.tmdb" in url:
                    url = url.replace("/w342/", "/original/")
                self.background.setImage(url.replace(" ", "%20"))


class Trailer(xbmcgui.WindowXMLDialog):
    def Start(self, item, trailers):
        self.item = item
        from channels import trailertools
        self.video_url, self.windows = trailertools.buscartrailer(self.item.clone(), trailers=trailers)

        self.doModal()


    def onInit(self):
        self.setCoordinateResolution(0)
        if not self.video_url:
            platformtools.dialog_notification("[COLOR crimson][B]Error[/B][/COLOR]", "[COLOR tomato]Vídeo no disponible[/COLOR]", 2)
            self.close()
        elif self.video_url == "no_video":
            self.close()
        else:
            new_video = False
            while True:
                if new_video:
                    self.doModal()
                xlistitem = xbmcgui.ListItem(path=self.video_url, thumbnailImage=self.item.thumbnail)
                pl = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
                pl.clear()
                pl.add(self.video_url, xlistitem)
                self.player = xbmc.Player()
                self.player.play(pl, windowed=True)
                while xbmc.Player().isPlaying():
                    xbmc.sleep(1000)
                self.close()
                self.video_url = None
                new_video = True
                self.windows[-1].doModal()
                try:
                    self.video_url = self.windows[-1].result
                    if not self.video_url:
                        break
                except:
                    break


    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU or action == ACTION_GESTURE_SWIPE_LEFT or action == 110 or action == 92:
            self.player.stop()
            self.close()

        elif action == ACTION_MOVE_LEFT:
             xbmc.executebuiltin('PlayerControl(Rewind)')
        elif action == ACTION_MOVE_RIGHT:
             xbmc.executebuiltin('PlayerControl(Forward)')
        elif action == ACTION_SELECT_ITEM:
             xbmc.executebuiltin('PlayerControl(Play)')
        elif action == 199 or action == ACTION_SHOW_FULLSCREEN or action == 9:
             xbmc.log("tuprimalafachaaa")
        if action == 13:
            self.close()


    def onClick(self, control):
        if control == self.getControl(2):
            self.player.pause()
        
        
def get_recomendations(item, infoLabels, recomendaciones):
    tipo = item.contentType
    if tipo != "movie":
        tipo = "tv"
    search = {'url': '%s/%s/recommendations' % (tipo, infoLabels['tmdb_id']), 'language': 'es', 'page': 1}
    reco_tmdb = tmdb.Tmdb(discover=search, tipo=tipo, idioma_busqueda="es")

    for i in range(0, len(reco_tmdb.results)):
        titulo = reco_tmdb.results[i].get("title", reco_tmdb.results[i].get("original_title", ""))
        if not titulo:
            titulo = reco_tmdb.results[i].get("name", reco_tmdb.results[i].get("original_name", ""))
        idtmdb = str(reco_tmdb.results[i].get("id"))
        thumbnail = reco_tmdb.results[i].get("poster_path", "")
        if thumbnail:
            thumbnail = 'http://image.tmdb.org/t/p/original' + thumbnail
        recomendaciones.append([idtmdb, titulo, thumbnail])


def get_filmaf(item, infoLabels):
    title = infoLabels["title"].replace(" ", "+")
    year = str(infoLabels.get("year", ""))
    url = "http://www.filmaffinity.com/es/advsearch.php?stext={0}&stype%5B%5D=title&country=&genre=&fromyear={1}&toyear={1}".format(title, year)
    data = scrapertools.downloadpage(url)

    tipo = "película"
    if item.contentType != "movie":
        tipo = "serie"
    url_filmaf = scrapertools.find_single_match(data, '<div class="mc-poster">\s*<a title="[^"]*" href="([^"]+)"')
    if url_filmaf:
        url_filmaf = "http://www.filmaffinity.com%s" % url_filmaf
        data = scrapertools.downloadpage(url_filmaf)

        rating = scrapertools.find_single_match(data, 'itemprop="ratingValue" content="([^"]+)"')
        if not rating:
            rating_filma = "[COLOR crimson][B]Sin puntuación[/B][/COLOR]"
        else:
            try:
                if float(rating) >= 5 and float(rating) < 8:
                    rating_filma = "[COLOR springgreen][B]%s[/B][/COLOR]" % rating
                elif float(rating) >= 8:
                    rating_filma = "[COLOR yellow][B]%s[/B][/COLOR]" % rating
                else:
                    rating_filma = "[COLOR crimson][B]%s[/B][/COLOR]" % rating
            except:
                import traceback
                logger.info(traceback.format_exc())
                rating_filma = "[COLOR crimson][B]%s[/B][/COLOR]" % rating
        plot = scrapertools.find_single_match(data, '<dd itemprop="description">(.*?)</dd>')
        plot = plot.replace("<br><br />", "\n")

        patron = '<div itemprop="reviewBody">(.*?)</div>.*?itemprop="author">(.*?)\s*<i alt="([^"]+)"'
        matches_reviews = scrapertools.find_multiple_matches(data, patron)
        critica = ""
        if matches_reviews:
            for review, autor, valoracion in matches_reviews:
                review = dhe(scrapertools.htmlclean(review))
                review += "\n" + autor
                if "positiva" in valoracion:
                    critica += "[COLOR green][B]%s[/B][/COLOR]\n\n" % review
                elif "neutral" in valoracion:
                    critica += "[COLOR yellow][B]%s[/B][/COLOR]\n\n" % review
                else:
                    critica += "[COLOR red][B]%s[/B][/COLOR]\n\n" % review
        else:
            critica = "[COLOR floralwhite][B]Esta %s no tiene críticas[/B][/COLOR]" % tipo

    else:
        critica = "[COLOR floralwhite][B]Esta %s no tiene críticas[/B][/COLOR]" % tipo
        rating_filma = "[COLOR crimson][B]Sin puntuación[/B][/COLOR]"
        plot = ""
    
    return critica, rating_filma, plot


def fanartv(item, infoLabels, images={}):
    from core import jsontools
    headers = [['Content-Type', 'application/json']]
    id_search = infoLabels.get('tvdb_id')
    if item.contentType != "movie" and not id_search:
        search = {'url': 'tv/%s/external_ids' % infoLabels['tmdb_id'], 'language': 'es'}
        ob_tmdb = tmdb.Tmdb(discover=search, idioma_busqueda='es')
        id_search = ob_tmdb.result.get("tvdb_id")
    elif item.contentType == "movie":
        id_search = infoLabels.get('tmdb_id')

    if id_search:
        if item.contentType == "movie":
            url = "http://webservice.fanart.tv/v3/movies/%s?api_key=cab16e262d72fea6a6843d679aa10300" \
                  % infoLabels['tmdb_id']
        else:
            url = "http://webservice.fanart.tv/v3/tv/%s?api_key=cab16e262d72fea6a6843d679aa10300" % id_search
        data = jsontools.load_json(scrapertools.downloadpage(url, headers=headers))
        if data and not "error message" in data:
            for key, value in data.items():
                if key not in ["name", "tmdb_id", "imdb_id", "thetvdb_id"]:
                    images[key] = value
    return images


def get_fonts(skin):
    data_font = ""
    fonts = {}
    if "confluence" in skin or "estuary" in skin or "refocus" in skin:
        fonts = {"10": "font10", "12": "font12", "16": "font16", "24": "font24_title", "30": "font30"}
    elif "aeonmq" in skin:
        fonts = {"10": "font_14", "12": "font_16", "16": "font_20", "24": "font_24", "30": "font_30"}
    elif "madnox" in skin:
        fonts = {"10": "Font_Reg22", "12": "Font_Reg26", "16": "Font_Reg32", "24": "Font_Reg38", "30": "Font_ShowcaseMainLabel2_Caps"}

    if not fonts:
        from core import filetools
        try:
            data_font = filetools.read(xbmc.translatePath(filetools.join('special://skin/1080i', 'Font.xml')), "r")
        except:
            try:
                data_font = filetoos.read(xbmc.translatePath(filetools.join('special://skin/720p', 'Font.xml')), "r")
            except:
                pass

    if data_font:
        fuentes = scrapertools.find_multiple_matches(data_font, "<name>([^<]+)<\/name>(?:<![^<]+>|)\s*<filename>[^<]+<\/filename>\s*<size>(\d+)<\/size>")
        sizes = []
        try:
            for name, size in fuentes:
                size = int(size)
                sizes.append([size, name])
            sizes.sort()
            fonts["10"] = sizes[0][1].lower()
            check = False
            if not 12 in sizes:
                for size, name in sizes:
                    if size != fonts["10"]:
                        fonts["12"] = name.lower()
                        check = True
                        break
            for size, name in sizes:
                if size == 12 and not check:
                    fonts["12"] = name.lower()
                elif size == 16:
                    fonts["16"] = name.lower()
                elif size == 24:
                    fonts["24"] = name.lower()
                elif size == 30:
                    fonts["30"] = name.lower()
                    break
                elif size > 30 and size <= 33:
                    fonts["30"] = name.lower()
                    break
        except:
            pass
    if not fonts:
        fonts = {"10": "font10", "12": "font12", "16": "font16", "24": "font24", "30": "font30"}

    return fonts


def translate(to_translate, to_language="auto", language="auto", i=0, bio=[]):
    '''Return the translation using google translate
        you must shortcut the langage you define (French = fr, English = en, Spanish = es, etc...)
        if you don't define anything it will detect it or use english by default
        Example:
        print(translate("salut tu vas bien?", "en"))
        hello you alright?'''
    import urllib2
    import urllib
    agents = {'User-Agent':"Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30)"}
    before_trans = 'class="t0">'
    to_translate = urllib.quote(to_translate.replace(" ", "+")).replace("%2B", "+")
    link = "http://translate.google.com/m?hl=%s&sl=%s&q=%s" % (to_language, language, to_translate)
    request = urllib2.Request(link, headers=agents)
    page = urllib2.urlopen(request).read()
    result = page[page.find(before_trans)+len(before_trans):]
    result = result.split("<")[0]
    result = re.sub(r"d>|nn", "", result)
    bio.append([i, result])
