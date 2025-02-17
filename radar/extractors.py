from radar import config


def getRadarImg(screenshot, radarToolsPos):
    radarToolsPosX = radarToolsPos[0]
    radarToolsPosY = radarToolsPos[1]
    x0 = radarToolsPosX - config.dimensions['width'] - 11
    x1 = x0 + config.dimensions['width']
    y0 = radarToolsPosY - 50
    y1 = y0 + config.dimensions['height']
    radarImage = screenshot[y0:y1, x0:x1]
    return radarImage