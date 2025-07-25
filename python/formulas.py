import urllib 
import os
import tempfile
import numpy as np 

from segequation import *

def point_create(line):
    figure = QgsVectorLayer("Point?crs=EPSG:26917", "Point Fig", "memory")
    pr = figure.dataProvider()
    pr.addAttributes([
        QgsField('x', QVariant.Double),
        QgsField('y', QVariant.Double)
    ])
    figure.updateFields()
    
    x = 0
    features = []
    last_len = 0 
    y2 = 0
    y1 = 0
    n = line.featureCount()
    i = 1
    for f in line.getFeatures():
        print(f'LENGTH: {f.attribute("length")}, ELEV: {f.attribute("_mean")}')
        length = f.attribute('length')
        y = f.attribute('_mean')
        if y is None or length is None:
            print('BAD FEATURE')
            continue  # skip bad features
        
        pt = QgsPointXY(x, y)
        new_feat = QgsFeature()
        new_feat.setGeometry(QgsGeometry.fromPointXY(pt))
        new_feat.setAttributes([x, y])
        features.append(new_feat)
        x += length
        if n == i - 1:
            y1 = y
        elif n == i:
            y2 = y
            last_len = length
        i += 1
    
    ## ADD LAST POINT
    m = ((y2 - y1) / (x - x - last_len))
    b = y2 - (m * x) 
    y = m * x + b
    pt = QgsPointXY(x, y)
    new_feat = QgsFeature()
    new_feat.setGeometry(QgsGeometry.fromPointXY(pt))
    new_feat.setAttributes([x, y])
    features.append(new_feat)

    pr.addFeatures(features)
    figure.updateExtents()
    return figure

class Formulas:
    def __init__(self, line, rast):
        bb_line = line.extent()

        xDist = bb_line.xMaximum() - bb_line.xMinimum()
        yDist = bb_line.yMaximum() - bb_line.yMinimum()
        print(str(xDist) + ', ' + str(yDist))
        
        rast_reproj = processing.run("gdal:warpreproject", {
            'INPUT': rast,
            'SOURCE_CRS': QgsCoordinateReferenceSystem(rast.crs().authid()),
            'TARGET_CRS': QgsCoordinateReferenceSystem('EPSG:26917'),
            'OPTIONS': 'COMPRESS=NONE|BIGTIFF=IF_NEEDED',
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })['OUTPUT']
        rast = QgsRasterLayer(rast_reproj, 'reprojected', 'gdal')

        clipped_rast = processing.run("gdal:cliprasterbyextent", {
            'INPUT': rast,
            'PROJWIN': f'{bb_line.xMinimum() - xDist},{bb_line.xMaximum() + xDist},{bb_line.yMinimum() - yDist},{bb_line.yMaximum() + yDist} [EPSG:26917]',
            'OPTIONS': 'COMPRESS=NONE|BIGTIFF=IF_NEEDED',
            'DATA_TYPE': 0,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })['OUTPUT']
        rast = QgsRasterLayer(clipped_rast, 'clipped', 'gdal')

        line = processing.run("native:splitlinesbylength", {
            'INPUT': line,
            'LENGTH': 10,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })['OUTPUT']

        line = processing.run("qgis:exportaddgeometrycolumns", {
            'INPUT': line,
            'CALC_METHOD': 1,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })['OUTPUT']

        buffered_line = processing.run("native:buffer", {
            'INPUT': line,
            'DISTANCE': 1e-06,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })['OUTPUT']

        buffered_line = processing.run("native:zonalstatisticsfb", {
            'INPUT': buffered_line,
            'INPUT_RASTER': rast,
            'RASTER_BAND': 1,
            'STATISTICS': [2],
            'OUTPUT': 'TEMPORARY_OUTPUT'
        })['OUTPUT']
        #QgsProject.instance().addMapLayer(buffered_line)
        point = point_create(buffered_line)
        #QgsProject.instance().addMapLayer(point)
        
        x_val = []
        y_val = []
        for feature in point.getFeatures():
            x_val.append(feature.attribute('x'))
            y_val.append(feature.attribute('y'))

        print(f'mean = {np.mean(y_val)}')
        print(f'last = {x_val[-1]}')
        # Create memory line layer
        layer = QgsVectorLayer("LineString?crs=EPSG:26917", "Elevation Line", "memory")
        pr = layer.dataProvider()

        seglist = []
        all_points = []

        for i in range(len(x_val) - 2):
            x_slice = x_val[i:i+3]
            y_slice = y_val[i:i+3]
            coefficients = np.polyfit(x_slice, y_slice, 2)
            a, b, c = coefficients
            seglist.append(SegEquation(x_val[i], coefficients))

            # Determine x_end differently for last iteration
            if i == len(x_val) - 3:
                x_end = x_val[-1]  # Last full fit — draw full segment
            else:
                x_end = x_val[i+1]  # Standard: draw only first third of parabola

            x_start = x_val[i]
            step = 0.05

            x = x_start
            while x <= x_end:
                y = a * x**2 + b * x + c
                all_points.append(QgsPointXY(x, y))
                x += step
        # Create one single feature from all points
        feature = QgsFeature()
        feature.setGeometry(QgsGeometry.fromPolylineXY(all_points))
        pr.addFeatures([feature])
        layer.updateExtents()

        self.elevLine = QgsProject.instance().addMapLayer(layer)
        self.segList = seglist

    def getSegList(self):
        return self.segList
        
    def getElevLine(self):
        return self.elevLine
print('completed.')
