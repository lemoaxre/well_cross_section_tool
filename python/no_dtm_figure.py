from segments import *
from formulas import *

scale_factor = 0

'''
Function: newPointLayer
Purpose: 
'''
def newPointLayer(dist, wells, order):
    # create memory point layer with CRS
    figure = QgsVectorLayer("Point?crs=EPSG:26917", "well figure", "memory")
    pr = figure.dataProvider()
    pr.addAttributes([
        QgsField('well_id', QVariant.Int),
        QgsField('depth', QVariant.Double)
    ])
    figure.updateFields()
    test = f"({', '.join(str(obj.getFirstWell()) for obj in order)})"
    print(test)
    wells.removeSelection()
    wells.selectByExpression('\"well_id\" IN' + test)
    features = wells.getSelectedFeatures()
    x = 0
    y = 0
    feature = QgsFeature()
    i = 0
    while features.nextFeature(feature):
        '''wells.removeSelection()
        wells.selectByExpression(f'"well_id" = {order[i].getFirstWell()}')
        features = wells.getSelectedFeatures()
        feature = next(features, None)
        depth = feature['depth']'''
        well_id_temp = feature.attribute('well_id')
        well_depth = feature.attribute('depth')
        f = QgsFeature()
        f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x, y)))
        f.setAttributes([well_id_temp, well_depth])
        pr.addFeature(f)
        if i < len(dist):
            x += dist[i]
            i += 1
    figure.updateExtents()
    return figure

def assignStarting(list):
    shared_well = None
    ## iterates through the segments.
    for i in range(len(list) - 1): 
        if i < len(list) - 2:
            current_wells = list[i].getWells() ## current segment wells.
            next_wells = list[i + 1].getWells() ## next segment wells.
            for j in current_wells: 
                is_shared = False ## if it appears in both this segment and next.
                for k in next_wells:
                    if j == k: ## set shared_well
                        shared_well = j
                        is_shared = True
                        break
                if not is_shared:
                    list[i].setFirstWell(j)
        else:
            current_seg = list[len(list)-2].getWells()
            last_seg = list[len(list)-3].getWells()
            is_shared = False
            list[len(list)-1] = Segment(len(list), list[len(list)-2].getWells())
            for i in last_seg:
                if i == current_seg[0]:
                    list[len(list)-2].setFirstWell(current_seg[0])
                    is_shared = True 
            if is_shared:
                list[len(list)-1].setFirstWell(current_seg[1])
                #list[len(list)-1].setFirstWell(current_seg[1])
            else: 
                list[len(list)-2].setFirstWell(1)
                list[len(list)-1].setFirstWell(0)

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
    
layers = iface.layerTreeView().selectedLayers()
well_layer = None
line_layer = None
rast_layer = None
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
            
    
    ## If both geometries exist, begin processing
    if well_layer is not None and line_layer is not None:
        reprojected = processing.run("native:reprojectlayer", {'INPUT':line_layer,'TARGET_CRS': 'EPSG:26917','OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
        exploded = processing.run("native:explodelines", {'INPUT':reprojected,'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
        buffered = processing.run("native:buffer", {'INPUT':exploded,'DISTANCE':1e-06, 'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
        QgsProject.instance().addMapLayer(buffered)
        
        well_seg = findSegWells(buffered, well_layer)
        print('indexing complete.')
        
        for i in well_seg:
            print('segment ' + str(i.getSegId()))
            print(i.getWells())
        QgsProject.instance().removeMapLayer(buffered.id())
        assignStarting(well_seg)
        print('Starting wells assigned.')
        exploded_geom = processing.run("qgis:exportaddgeometrycolumns", {'INPUT':exploded,
            'CALC_METHOD':0,
            'OUTPUT':'TEMPORARY_OUTPUT'})['OUTPUT']
        lengths = [None] * exploded_geom.featureCount()
        pos = 0 
        for i in exploded_geom.getFeatures():
            print('segment ' + str(i.id()) + ': ' + str(i.attribute('length')))
            lengths[pos] = i.attribute('length')
            pos += 1
        if scale_factor > 0: 
            lengths = [x / sum(lengths) * scale_factor for x in lengths]
        for i in range(len(well_seg)):
            print('Well ' + str(well_seg[i].getSegId()) + ': ' + 
                str(well_seg[i].getFirstWell()))
                
        figure = newPointLayer(lengths, well_layer, well_seg)
        #QgsProject.instance().addMapLayer(figure)
        s = QgsSymbol.defaultSymbol(figure.geometryType())
        s.deleteSymbolLayer(0)
        
        s.appendSymbolLayer(QgsGeometryGeneratorSymbolLayer.create({
        'geometryType': 'LineString',
        'symbolType': 'line',
        'geometryModifier': '''
        make_line(
            geometries_to_array(
                collect($geometry, group_by:=$y)
            )
        )'''}))
        s.appendSymbolLayer(QgsGeometryGeneratorSymbolLayer.create({
        'geometryType': 'LineString',
        'symbolType': 'line',
        'geometryModifier': '''
        make_line(
            $geometry,
            make_point(x($geometry), y($geometry) - "depth")
        )
        '''}))
        figure.renderer().setSymbol(s)
        figure.triggerRepaint()
        print('Script finished.')
        
        elev_line = Formulas(reprojected, rast_layer)
        print(elev_line.getSegList()[3].getDist())
    else:
        print('Invalid geometry types, ensure you are using wells and a line layer.')
