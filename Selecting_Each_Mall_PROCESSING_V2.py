##RyersonGeo - Primary and Secondary Market Area=name
##Huff_Model_Layer=vector
##Mall=field Huff_Model_Layer
##Census_Layer=vector
##Population_Data=field Census_Layer
##Other_Census_Data=multiple field Census_Layer
##Mall_Layer_Name= string test
##PDF_file=output file pdf

from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os

# Load the huff model layer
ori_huff_model = processing.getObject(Huff_Model_Layer)
# Load the census layer
census_layer = processing.getObject(Census_Layer)

root = QgsProject.instance().layerTreeRoot()

# Remove old huff_model layer if script was run previously
try:
    last_layer = QgsMapLayerRegistry.instance().mapLayersByName(Mall_Layer_Name)[0]
    QgsMapLayerRegistry.instance().removeMapLayers([last_layer])
    del last_layer
except IndexError:
    child1 = root.children()[1]
    if child1.name() == census_layer.name():
        ids = root.findLayerIds()
        last_layer = root.findLayer(ids[0])
        print last_layer.name()
        root.removeChildNode(last_layer)

# Make a copy of the huff model layer to work with so that all changes made to copy only keeping original data intact
huff_model = QgsVectorLayer("Polygon?crs=epsg:4326", Mall_Layer_Name, "memory")
huff_model_data = huff_model.dataProvider()

huff_model.startEditing()

attr = ori_huff_model.dataProvider().fields().toList()
huff_model_data.addAttributes(attr)
huff_model.updateFields()

feat = QgsFeature()
for elem in ori_huff_model.getFeatures():
    feat.setGeometry(elem.geometry())
    feat.setAttributes(elem.attributes())
    huff_model.addFeatures([feat])
    huff_model.updateExtents()
    
# Choose the mall to find the primary and secondary market areas
mall = ori_huff_model.fieldNameIndex(Mall)
for field in huff_model.fields():
    field_id = huff_model.fieldNameIndex(field.name())
    #print ">>> Field name: {} Field ID: {}".format(field.name(), field_id)
    if mall == field.name():
        mall = huff_model.fieldNameIndex(field.name())
        #print "<<< mall ID: {}".format(mall)
        break

col_num = int(mall)

# Create two new fields that will only show the primary and secondary market areas based on selected probabilities
primary = QgsField('Primary', QVariant.Double, "double",  2,  2)
huff_model.addAttribute(primary)
index_pri = huff_model.fieldNameIndex('Primary')

secondary = QgsField('Secondary', QVariant.Double, "double",  2,  2)
huff_model.addAttribute(secondary)
index_sec = huff_model.fieldNameIndex('Secondary')

pri_pop = QgsField('PRI_POP', QVariant.Int)
huff_model.addAttribute(pri_pop)
idx_pri_pop = huff_model.fieldNameIndex('PRI_POP')

sec_pop = QgsField('SEC_POP', QVariant.Int)
huff_model.addAttribute(sec_pop)
idx_sec_pop = huff_model.fieldNameIndex('SEC_POP')

for feature in huff_model.getFeatures():
    probability = feature.attributes()
    ctuid = feature["CTUID"]
    if not probability[col_num]:
        print ("This mall does not exist")
    else:
        # Primary market values will go into this column
        if probability[col_num] >= .6:
            #print("Primary market area: {} ({})".format(ctuid, probability[col_num]))
            huff_model.changeAttributeValue(feature.id(), index_pri, probability[col_num])
        # Secondary market values will go into this column
        if .4 <= probability[col_num] < .6:
            #print("Secondary market area: {} ({})".format(ctuid, probability[col_num]))
            huff_model.changeAttributeValue(feature.id(), index_sec, probability[col_num])

# Delete all other features (rows) that do not have a probability in the primary and the secondary column
expr = QgsExpression("Primary is NULL and Secondary is NULL")
for f in huff_model.getFeatures(QgsFeatureRequest(expr)):
    huff_model.deleteFeature(f.id())

huff_model.updateExtents()
huff_model.commitChanges()

# Add newly created layer to map
reg = QgsMapLayerRegistry.instance()
reg.addMapLayer(huff_model)

# Join the census layer to the newly created layer to show specific demographic data. 
targetLyr = QgsMapLayerRegistry.instance().mapLayersByName (Mall_Layer_Name)[0]
censusLyr = QgsMapLayerRegistry.instance().mapLayersByName(census_layer.name())[0]

mycensusLyr = root.findLayer(censusLyr.id())
censusClone = mycensusLyr.clone()
parent = mycensusLyr.parent()
parent.insertChildNode(1, censusClone)
parent.removeChildNode(mycensusLyr)

# Ensuring the fields selected for the join are ordered in the same way they are shown in the census layer attribute table
census_attr = set(Other_Census_Data.split(';'))
if 'CTUID' in census_attr:
    # Remove the field being joined from selected field list
    census_attr.remove('CTUID')
if Population_Data not in census_attr:
    # Make sure population data is in the joined table to calculate new fields
    census_attr.add(Population_Data)
fields = census_layer.pendingFields()
field_names = [field.name() for field in fields]
final_census_attr = sorted(census_attr, key=lambda x: field_names.index(x))

# Set properties for the join
targetField = 'CTUID'
inField = 'CTUID'
joinObject = QgsVectorJoinInfo()
joinObject.joinLayerId = censusLyr.id()
joinObject.joinFieldName = inField
joinObject.targetFieldName = targetField
joinObject.memoryCache = True
joinObject.setJoinFieldNamesSubset(final_census_attr)
joinObject.prefix = ''
print(targetLyr.addJoin(joinObject))  # You should get True as response.
targetLyr.addJoin(joinObject)

huff_model.startEditing()

expression = QgsExpression("to_int(Primary * " + Population_Data+ ")")
expression.prepare(huff_model.pendingFields())
for feature in huff_model.getFeatures():
    value = expression.evaluate(feature)
    feature[idx_pri_pop] = value
    huff_model.updateFeature(feature)

expression2 = QgsExpression("to_int(Secondary * " + Population_Data + ")")
expression2.prepare(huff_model.pendingFields())
for feature in huff_model.getFeatures():
    value = expression2.evaluate(feature)
    feature[idx_sec_pop] = value
    huff_model.updateFeature(feature)

# Delete all other columns except for the CTUID, Primary, Secondary columns
fields = []

fieldnames = {'CTUID', 'Primary', 'Secondary', 'PRI_POP', 'SEC_POP'}
for field in huff_model.fields():
    if field.name() not in fieldnames:
        fields.append(huff_model.fieldNameIndex(field.name()))
        # print(fields.append(huff_model.fieldNameIndex(field.name())))

huff_model.deleteAttributes(fields)
huff_model.commitChanges()

# Make sure that the newly created and joined layer is the active layer.
huff_model = iface.activeLayer()

# Create the attribute using the map composer in QGIS and show the output in PDF format.
mapRenderer = iface.mapCanvas().mapRenderer()
c = QgsComposition(mapRenderer)
c.setPlotStyle(QgsComposition.Print)
x, y = 0, 0
w, h = c.paperWidth(), c.paperHeight()
composerMap = QgsComposerMap(c, x, y, w, h)

table = QgsComposerAttributeTable(c)
table.setComposerMap(composerMap)
table.setScale(1)
table.setVectorLayer(huff_model)
table.setMaximumNumberOfFeatures(huff_model.featureCount())
c.addItem(table)

# Checks for the existence of a file with the same name and removes it.
if os.path.isfile(PDF_file):
    os.remove(PDF_file)

# Set the properties of the PDF which will take and show the attribute table
printer = QPrinter()
printer.setOutputFormat(QPrinter.PdfFormat)
printer.setOutputFileName(PDF_file)
printer.setPaperSize(QSizeF(c.paperWidth(), c.paperHeight()), QPrinter.Millimeter)
printer.setFullPage(True)

pdfPainter = QPainter(printer)
paperRectMM = printer.pageRect(QPrinter.Millimeter)
paperRectPixel = printer.pageRect(QPrinter.DevicePixel)
c.render(pdfPainter, paperRectPixel, paperRectMM)
pdfPainter.end()
