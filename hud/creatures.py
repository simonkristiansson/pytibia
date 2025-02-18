import math
from re import A
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
import hud.core
import utils.core
import utils.image
import utils.matrix
import wiki.creatures
from time import time


lifeBarBlackPixelsMapper = np.array([
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26,
    480, 506,
    960, 986,
    1440, 1441, 1442, 1443, 1444, 1445, 1446, 1447, 1448, 1449, 1450, 1451, 1452, 1453, 1454, 1455, 1456, 1457, 1458, 1459, 1460, 1461, 1462, 1463, 1464, 1465, 1466
])
lifeBarFlattenedImg = np.zeros(lifeBarBlackPixelsMapper.size)
hudWidth = 480
creaturesNamesHashes = {}
for monster in wiki.creatures.creatures:
    creaturesNamesHashes[monster] = utils.image.loadAsGrey(
        'hud/images/monsters/{}.png'.format(monster))
creatureType = np.dtype([
    ('name', np.str_, 64),
    ('healthPercentage', np.uint8),
    ('isBeingAttacked', np.bool_),
    ('slot', np.uint8, (2,)),
    ('gameCoordinate', np.uint16, (3,)),
    ('windowCoordinate', np.uint32, (2,))
])


def cleanCreatureName(creatureName):
    creatureName = np.where(creatureName == 29, 0, creatureName)
    creatureName = np.where(creatureName == 91, 0, creatureName)
    creatureName = np.where(creatureName == 113, 0, creatureName)
    creatureName = np.where(creatureName == 152, 0, creatureName)
    creatureName = np.where(creatureName == 170, 0, creatureName)
    creatureName = np.where(creatureName == 192, 0, creatureName)
    return creatureName


def getClosestCreature(creatures, coordinate, walkableFloorsSqms):
    hasNoCreatures = len(creatures) == 0
    if hasNoCreatures:
        return None
    (x, y) = utils.core.getPixelFromCoordinate(coordinate)
    hudwalkableFloorsSqms = walkableFloorsSqms[y-5:y+6, x-7:x+8]
    hudwalkableFloorsSqmsCreatures = np.zeros((11, 15))
    creaturesSlots = creatures['slot'][:, [1, 0]]
    hudwalkableFloorsSqmsCreatures[creaturesSlots[:,
                                                  0], creaturesSlots[:, 1]] = 1
    adjacencyMatrix = utils.matrix.getAdjacencyMatrix(hudwalkableFloorsSqms)
    sqmsGraph = csr_matrix(adjacencyMatrix)
    playerHudIndex = 82
    sqmsGraphWeights = dijkstra(
        sqmsGraph, directed=True, indices=playerHudIndex, unweighted=False)
    creaturesIndexes = np.nonzero(
        hudwalkableFloorsSqmsCreatures.flatten() == 1)[0]
    creaturesGraphWeights = np.take(sqmsGraphWeights, creaturesIndexes)
    nonTargetCreaturesIndexes = np.where(creaturesGraphWeights == np.inf)[0]
    creaturesIndexes = np.delete(creaturesIndexes, nonTargetCreaturesIndexes)
    creaturesGraphWeights = np.delete(
        creaturesGraphWeights, nonTargetCreaturesIndexes)
    hasOnlyNonTargetCreatures = len(creaturesGraphWeights) == 0
    if hasOnlyNonTargetCreatures:
        return None
    creaturesDistances = np.where(
        creaturesGraphWeights == np.amin(creaturesGraphWeights))[0]
    closestCreatureHudIndex = creaturesIndexes[np.random.choice(
        creaturesDistances)]
    creatureSlot = [closestCreatureHudIndex %
                    15, closestCreatureHudIndex // 15]
    closestCreatureIndex = np.where(
        (creatures['slot'] == creatureSlot).all(axis=1))[0][0]
    closestCreature = creatures[closestCreatureIndex]
    return closestCreature


def getCreaturesBars(hudImg):
    # TODO: improve clean code
    flattenedHudImg = hudImg.flatten()
    blackPixelsIndexes = np.nonzero(flattenedHudImg == 0)[0]
    maxBlackPixelIndex = 168960 - 1468
    allowedBlackPixelsIndexes = np.nonzero(
        blackPixelsIndexes < maxBlackPixelIndex)[0]
    blackPixelsIndexes = np.take(blackPixelsIndexes, allowedBlackPixelsIndexes)
    noBlackPixels = blackPixelsIndexes.size == 0
    if noBlackPixels:
        return np.array([])
    blackPixelsIndexesDiff = np.diff(blackPixelsIndexes)
    blackPixelsIndexesDiff = np.where(blackPixelsIndexesDiff == 1, 1, 0)
    cumulativeOfBlackPixelsIndexesDiff = np.cumsum(blackPixelsIndexesDiff)
    corr = np.diff(np.hstack(
        ((0,), cumulativeOfBlackPixelsIndexesDiff[blackPixelsIndexesDiff == 0])))
    a2 = blackPixelsIndexesDiff.copy()
    a2[blackPixelsIndexesDiff == 0] -= corr
    f = a2.cumsum()
    h = np.where(f == 26)[0]
    h = h - 25
    blackPixelsIndexes = np.take(blackPixelsIndexes, h)
    blackPixelsIndexes2d = np.broadcast_to(
        blackPixelsIndexes, (lifeBarBlackPixelsMapper.size, blackPixelsIndexes.size))
    blackPixelsIndexes2d = np.transpose(blackPixelsIndexes2d)
    z = np.add(blackPixelsIndexes2d, lifeBarBlackPixelsMapper)
    pixelsColorsIndexes = np.take(hudImg, z)
    g = (pixelsColorsIndexes == lifeBarFlattenedImg).all(1)
    possibleCreatures = np.nonzero(g)[0]
    hasNoCreaturesBars = possibleCreatures.size == 0
    if hasNoCreaturesBars:
        return np.array([])
    creaturesBars = np.take(blackPixelsIndexes, possibleCreatures)
    creaturesBarsX = creaturesBars % hudWidth
    creaturesBarsY = creaturesBars // hudWidth
    creaturesBarsXY = np.column_stack((creaturesBarsX, creaturesBarsY))
    return creaturesBarsXY


def getCreatures(screenshot, battleListCreatures, radarCoordinate=None):
    """
    TODO:
    - Find a way to avoid 3 calculation times when comparing names since some words have a wrong location
    - Whenever the last species is left, avoid loops and resolve species immediately for remaining creatures bars
    """
    hudCoordinate = hud.core.getCoordinate(screenshot)
    hudImg = hud.core.getImgByCoordinate(screenshot, hudCoordinate)
    creaturesBars = getCreaturesBars(hudImg)
    creatures = np.array([], dtype=creatureType)
    hasNoCreaturesBars = len(creaturesBars) == 0
    if hasNoCreaturesBars:
        return creatures
    hasNoBattleListCreatures = len(battleListCreatures) == 0
    if hasNoBattleListCreatures:
        return creatures
    centersBars = np.broadcast_to([239, 175], (len(creaturesBars), 2))
    absolute = np.absolute(creaturesBars - centersBars)
    power = np.power(absolute, 2)
    sum = np.sum(power, axis=1)
    sqrt = np.sqrt(sum)
    creaturesBarsSortedInxes = np.argsort(sqrt)
    for creatureBarSortedIndex in creaturesBarsSortedInxes:
        creatureBar = creaturesBars[creatureBarSortedIndex]
        nonCreaturesForCurrentBar = {}
        battleListCreaturesCount = len(battleListCreatures)
        for battleListIndex in range(battleListCreaturesCount):
            battleListCreature = battleListCreatures[battleListIndex]
            creatureName = battleListCreature['name']
            creatureTypeAlreadyTried = creatureName in nonCreaturesForCurrentBar
            if creatureTypeAlreadyTried:
                continue
            _, creatureNameWidth = creaturesNamesHashes[creatureName].shape
            (creatureBarX, creatureBarY) = creatureBar
            creatureBarY0 = creatureBarY - 13
            creatureBarY1 = creatureBarY0 + 11
            creatureNameImgHalfWidth = math.floor(creatureNameWidth / 2)
            leftDiff = max(creatureNameImgHalfWidth - 13, 0)
            gapLeft = 0 if creatureBarX > leftDiff else leftDiff - creatureBarX
            gapInnerLeft = 0 if creatureNameWidth > 27 else math.ceil(
                (27 - creatureNameWidth) / 2)
            rightDiff = max(creatureNameWidth -
                            creatureNameImgHalfWidth - 14, 0)
            gapRight = 0 if hud.core.hudSize[0] > (
                creatureBarX + 27 + rightDiff) else creatureBarX + 27 + rightDiff - hud.core.hudSize[0]
            gapInnerRight = 0 if creatureNameWidth > 27 else math.floor(
                (27 - creatureNameWidth) / 2)
            startingX = max(0, creatureBarX - creatureNameImgHalfWidth +
                            13 + gapLeft + gapInnerLeft - gapRight - gapInnerRight)
            endingX = min(480, creatureBarX + creatureNameImgHalfWidth +
                          13 + gapLeft + gapInnerLeft - gapRight - gapInnerRight)
            creatureNameImg = creaturesNamesHashes[creatureName].copy()
            creatureWithDirtNameImg = hudImg[creatureBarY0:creatureBarY1,
                                             startingX:endingX]
            if creatureNameImg.shape[1] != creatureWithDirtNameImg.shape[1]:
                creatureWithDirtNameImg = hudImg[creatureBarY0:creatureBarY1,
                                                 startingX:endingX + 1]
            # TODO: avoid cleaning matrix, search directly by specific colours
            creatureWithDirtNameImg = cleanCreatureName(
                creatureWithDirtNameImg)
            creatureDidMatch = utils.matrix.hasMatrixInsideOther(
                creatureWithDirtNameImg, creatureNameImg)
            if creatureDidMatch:
                creature = makeCreature(
                    creatureName, creatureBar, hudCoordinate, hudImg=hudImg, radarCoordinate=radarCoordinate)
                creaturesToAppend = np.array([creature], dtype=creatureType)
                creatures = np.append(creatures, creaturesToAppend)
                battleListCreatures = np.delete(
                    battleListCreatures, battleListIndex)
                break
            creatureNameImg2 = creaturesNamesHashes[creatureName].copy()
            creatureWithDirtNameImg2 = hudImg[creatureBarY0:creatureBarY1,
                                              startingX+1:endingX+1]
            if creatureNameImg2.shape[1] != creatureWithDirtNameImg2.shape[1]:
                creatureNameImg2 = creatureNameImg2[:,
                                                    0:creatureNameImg2.shape[1] - 1]
            creatureWithDirtNameImg2 = cleanCreatureName(
                creatureWithDirtNameImg2)
            creatureDidMatch = utils.matrix.hasMatrixInsideOther(
                creatureWithDirtNameImg2, creatureNameImg2)
            if creatureDidMatch:
                creature = makeCreature(
                    creatureName, creatureBar, hudCoordinate, hudImg=hudImg, radarCoordinate=radarCoordinate)
                creaturesToAppend = np.array([creature], dtype=creatureType)
                creatures = np.append(creatures, creaturesToAppend)
                battleListCreatures = np.delete(
                    battleListCreatures, battleListIndex)
                break
            creatureWithDirtNameImg3 = hudImg[creatureBarY0:creatureBarY1,
                                              startingX:endingX - 1]
            creatureWithDirtNameImg3 = cleanCreatureName(
                creatureWithDirtNameImg3)
            creatureNameImg3 = creaturesNamesHashes[creatureName].copy()
            creatureNameImg3 = creatureNameImg3[:, 1:creatureNameImg3.shape[1]]
            if creatureWithDirtNameImg3.shape[1] != creatureNameImg3.shape[1]:
                creatureNameImg3 = creatureNameImg3[:,
                                                    0:creatureNameImg3.shape[1] - 1]
            creatureDidMatch = utils.matrix.hasMatrixInsideOther(
                creatureWithDirtNameImg3, creatureNameImg3)
            if creatureDidMatch:
                creature = makeCreature(
                    creatureName, creatureBar, hudCoordinate, hudImg=hudImg, radarCoordinate=radarCoordinate)
                creaturesToAppend = np.array([creature], dtype=creatureType)
                creatures = np.append(creatures, creaturesToAppend)
                battleListCreatures = np.delete(
                    battleListCreatures, battleListIndex)
                break
            nonCreaturesForCurrentBar[creatureName] = True
    return creatures


def getDifferentCreaturesBySlots(previousHudCreatures, currentHudCreatures, slots):
    previousHudCreaturesBySlots = np.array(
        [], dtype=creatureType)
    currentHudCreaturesBySlots = np.array(
        [], dtype=creatureType)
    differentCreatures = np.array([], dtype=creatureType)
    for previousHudCreature in previousHudCreatures:
        if np.isin(previousHudCreature['slot'], slots).all():
            previousHudCreaturesBySlots = np.append(
                previousHudCreaturesBySlots, [previousHudCreature])
    for currentHudCreature in currentHudCreatures:
        if np.isin(currentHudCreature['slot'], slots).all():
            currentHudCreaturesBySlots = np.append(
                currentHudCreaturesBySlots, [currentHudCreature])
    for previousHudCreature in previousHudCreaturesBySlots:
        creatureDoesNotExists = True
        for currentHudCreature in currentHudCreatures:
            previousHudCreatureHash = utils.core.hashitHex(
                previousHudCreature)
            currentHudCreatureHash = utils.core.hashitHex(
                currentHudCreature)
            if previousHudCreatureHash == currentHudCreatureHash:
                creatureDoesNotExists = False
                break
        if creatureDoesNotExists:
            differentCreatures = np.append(
                differentCreatures, [previousHudCreature])
    return differentCreatures


def getNearestCreaturesCount(creatures):
    hudWalkableFloorsSqmsCreatures = np.zeros((11, 15), dtype=np.uint)
    xySlots = creatures['slot'][:, [1, 0]]
    hudWalkableFloorsSqmsCreatures[xySlots[:, 0], xySlots[:, 1]] = 1
    indicesOfNearestCreatures = hudWalkableFloorsSqmsCreatures[
        [4, 4, 4, 5, 5, 6, 6, 6],
        [6, 7, 8, 6, 8, 6, 7, 8]
    ]
    nearestCreaturesCount = np.sum(indicesOfNearestCreatures)
    return nearestCreaturesCount


def hasTargetToCreatureByIndex(hudWalkableFloorsSqms, hudCreaturesSlots, index):
    creaturesSlots = hudCreaturesSlots[:, [1, 0]]
    hudWalkableFloorsSqms[creaturesSlots[:, 0], creaturesSlots[:, 1]] = 0
    hudWalkableFloorsSqms[index[1], index[0]] = 1
    adjacencyMatrix = utils.matrix.getAdjacencyMatrix(hudWalkableFloorsSqms)
    graph = csr_matrix(adjacencyMatrix)
    playerHudIndex = 82
    graphWeights = dijkstra(graph, directed=True,
                            indices=playerHudIndex, unweighted=False)
    graphWeights = graphWeights.reshape(11, 15)
    creatureGraphValue = graphWeights[index[1], index[0]]
    hasTarget = creatureGraphValue != np.inf
    return hasTarget


def makeCreature(creatureName, coordinate, hudCoordinate, hudImg=None, radarCoordinate=None):
    (hudCoordinateX, hudCoordinateY, _, _) = hudCoordinate
    (x, y) = coordinate
    extraY = 0 if y <= 27 else 15
    xCoordinate = x - 3 + extraY
    yCoordinate = y + 5 + extraY
    xSlot = round(xCoordinate / 32)
    xSlot = 14 if xSlot > 14 else xSlot
    ySlot = 0 if y <= 27 else round(yCoordinate / 32)
    ySlot = 10 if ySlot > 10 else ySlot
    healthPercentage = 100
    borderedCreatureImg = hudImg[y+5:y+5+32, x-3:x-3+32]
    isBeingAttacked = np.sum(np.where(np.logical_or(
        borderedCreatureImg == 76, borderedCreatureImg == 166), 1, 0)) > 10
    slot = (xSlot, ySlot)
    gameCoordinateX = radarCoordinate[0] - 7 + xSlot
    gameCoordinateY = radarCoordinate[1] - 5 + ySlot
    gameCoordinate = (gameCoordinateX, gameCoordinateY, radarCoordinate[2])
    windowCoordinate = (hudCoordinateX + xCoordinate,
                        hudCoordinateY + yCoordinate)
    creature = (creatureName, healthPercentage, isBeingAttacked,
                slot, gameCoordinate, windowCoordinate)
    return creature
