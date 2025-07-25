'''
# Well Cross-section Generator
# Last updated: 07/25/2025
# While running, select 
'''
from segments import *
from formulas import *

scale_factor = 3

def findSegWells(line_layer, wells):
    f = QgsFeature()
    features = line_layer.getFeatures()
    well_seg = [None] * (line_layer.featureCount() + 1)
    index = 0
    while features.nextFeature(f):
        line_layer.removeSelection()
        line_layer.select(f.id())
        well_layer.removeSelection()
        processing.run("native:selectbylocation", {'INPUT':wells,
                        'PREDICATE':[0],
                        'INTERSECT':QgsProcessingFeatureSourceDefinition(line_layer.id(), 
                            selectedFeaturesOnly=True, featureLimit=-1, 
                            geometryCheck=QgsFeatureRequest.GeometryAbortOnInvalid),
                        'METHOD':0})
        well_list = [None] * wells.selectedFeatureCount()
        i2 = 0 
        for i in wells.getSelectedFeatures():
            well_list[i2] = i.attribute('well_id')
            i2 += 1
        well_seg[index] = Segment(f.id(), well_list)
        index += 1
    well_seg[len(well_seg)-1] = Segment(len(well_seg), None)
    return well_seg

well_layer = None
line_layer = None
rast_layer = None
layers = iface.layerTreeView().selectedLayers()
if len(layers) == 3: 
    ## Load in the layers, check that the geometry is correct.
    for i in layers:
        if i.type() == QgsMapLayer.VectorLayer:
            if i.geometryType() == 0 and well_layer is None: 
                well_layer = i
            elif i.geometryType() == 1 and line_layer is None: 
                line_layer = i
        else: 
            rast_layer = i
if line_layer is not None and well_layer is not None:
    line_layer = processing.run("native:reprojectlayer", {'INPUT':line_layer,
        'TARGET_CRS':QgsCoordinateReferenceSystem('EPSG:26917'),
        'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    
    elev_line = Formulas(line_layer, rast_layer)
    
    well_layer = processing.run("native:reprojectlayer", {'INPUT':well_layer,
        'TARGET_CRS':QgsCoordinateReferenceSystem('EPSG:26917'),
        'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    
    buffered_ln = processing.run("native:buffer", {'INPUT':line_layer,
        'DISTANCE':1e-06,
        'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    well_layer = processing.run("native:clip", {'INPUT':well_layer,'OVERLAY':buffered_ln,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    well_layer = processing.run("native:deleteduplicategeometries", {'INPUT':well_layer,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    
    line_geom = next(line_layer.getFeatures()).geometry()

    results = []

    for f in well_layer.getFeatures():
        dist = line_geom.lineLocatePoint(f.geometry())
        results.append((dist, f.attribute('well_id')))

    results.sort()
    
    print(results)
    
    for i in range(len(results)):
        segList = elev_line.getSegList()
        for j in range(len(segList)):
            if segList[j].onSeg(results[i][0]):
                print(f'x: {results[i][0]}, y: {segList[j].getYPos(results[i][0])}')
                break
            elif j == len(segList) - 1:
                print(f'x: {results[i][0]}, y: {segList[j].getYPos(results[i][0])}')
    
    figure = QgsVectorLayer("Point?crs=EPSG:26917", "well figure", "memory")
    pr = figure.dataProvider()
    pr.addAttributes([
        QgsField('well_id', QVariant.Int),
        QgsField('depth', QVariant.Double)
    ])
    
    figure.updateFields()
    features = well_layer.getFeatures()
    feature = QgsFeature()
    i = 0
    while features.nextFeature(feature):
        x = results[i][0]
        for j in range(len(segList)):
            if segList[j].onSeg(results[i][0]):
                y = segList[j].getYPos(x)
                break
            elif j == len(segList) - 1:
                y = segList[j].getYPos(x)
        well_id_temp = feature.attribute('well_id')
        well_depth = feature.attribute('depth')
        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
        f.setAttributes([well_id_temp, well_depth])
        pr.addFeature(f)
        if i < len(results):
            i += 1
    figure.updateExtents()
    figure = processing.run("native:snapgeometries", {'INPUT':figure,
        'REFERENCE_LAYER':elev_line.getElevLine(),
        'BEHAVIOR': 0,
        'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
    symbol = elev_line.getElevLine().renderer().symbol()
    symbol.setColor(QColor(0,0,0))
    
    elev_line.getElevLine().triggerRepaint()
    
    s = QgsSymbol.defaultSymbol(figure.geometryType())
    s.deleteSymbolLayer(0)
        
    s.appendSymbolLayer(QgsGeometryGeneratorSymbolLayer.create({
    'geometryType': 'LineString',
    'symbolType': 'line',
    'geometryModifier': '''
    make_line(
        $geometry,
        make_point(x($geometry), y($geometry) - "depth" * {})
    )
    '''.format(scale_factor)}))
    figure.renderer().setSymbol(s)
    figure.triggerRepaint()
    
    figure.setName('Wells')
    QgsProject.instance().addMapLayer(figure)
    figure.reload()