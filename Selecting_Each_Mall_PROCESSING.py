##RyersonGeo - Primary and Secondary Market Area=name

##Huff_Model_Layer=vector
##Mall=field Huff_Model_Layer
##PDF_file=output file

from qgis.core import *
from qgis.gui import *
from qgis.utils import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os

# Load the huff model layer
ori_huff_model = processing.getObject(Huff_Model_Layer)
# Choose the mall to find the primary and secondary market areas
mall = ori_huff_model.fieldNameIndex(Mall)

# Make a copy of the huff model layer to work with so that all changes made to copy only keeping original data intact
huff_model = QgsVectorLayer("Polygon?crs=epsg:4326", "Huff_Model", "memory")
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

# Checks that the current layer is valid
if huff_model.isValid():
    print "Model is valid."
else:
    print "Invalid Model."

for field in huff_model.fields():
    field_id = huff_model.fieldNameIndex(field.name())
    print ">>> Field name: {} Field ID: {}".format(field.name(), field_id)
    if mall == field.name():
        mall = huff_model.fieldNameIndex(field.name())
        print "<<< mall ID: {}".format(mall)
        break

col_num = int(mall)
print col_num

# Create two new fields that will only show the primary and secondary market areas based on selected probabilities
primary = QgsField('Primary', QVariant.Double)
huff_model.addAttribute(primary)
index_pri = huff_model.fieldNameIndex('Primary')

secondary = QgsField('Secondary', QVariant.Double)
huff_model.addAttribute(secondary)
index_sec = huff_model.fieldNameIndex('Secondary')

for feature in huff_model.getFeatures():
    probability = feature.attributes()
    ctuid = feature["CTUID"]
    if not probability[col_num]:
        print ("This mall does not exist")
    else:
        # Primary market values will go into this column
        if probability[col_num] >= .6:
            print("Primary market area: {} ({})".format(ctuid, probability[col_num]))
            huff_model.changeAttributeValue(feature.id(), index_pri, probability[col_num])
        # Secondary market values will go into this column
        if .4 <= probability[col_num] < .6:
            print("Secondary market area: {} ({})".format(ctuid, probability[col_num]))
            huff_model.changeAttributeValue(feature.id(), index_sec, probability[col_num])

# Delete all other columns except for the CTUID, Primary, Secondary columns
fields = []

fieldnames = {'CTUID', 'Primary', 'Secondary'}
for field in huff_model.fields():
    if field.name() not in fieldnames:
        fields.append(huff_model.fieldNameIndex(field.name()))
        print(fields.append(huff_model.fieldNameIndex(field.name())))

huff_model.deleteAttributes(fields)

# Delete all other features (rows) that do not have a probability in the primary and the secondary column
expr = QgsExpression("\"Primary\" is NULL and \"Secondary\" is NULL")
for f in huff_model.getFeatures(QgsFeatureRequest(expr)):
    huff_model.deleteFeature(f.id())

huff_model.commitChanges()

# Making sure that only one copy layer exists at a time, if running the script multiple times with different malls
layers = QgsMapLayerRegistry.instance().mapLayers()
for name, layer in layers.iteritems():
    if layer.name() == "Huff_Model":
        print "It exists"
        if "Huff_Model" in name:
            QgsMapLayerRegistry.instance().removeMapLayer(layer)
    else:
        print "Does not exist"

# Add newly formatted layer to map
reg = QgsMapLayerRegistry.instance()
reg.addMapLayer(huff_model)

# Join the census layer to the newly created layer to show specific demographic data. Currently the full table is
# joined but specific columns can be chose if an entire table join is unnecessary.
targetLyr = QgsMapLayerRegistry.instance().mapLayersByName("Huff_Model")[0]
censusLyr = QgsMapLayerRegistry.instance().mapLayersByName("TorontoCMA_2006census_region")[0]

root = QgsProject.instance().layerTreeRoot()

mytargetLyr = root.findLayer(targetLyr.id())
targetClone = mytargetLyr.clone()
parent = mytargetLyr.parent()
parent.insertChildNode(0, targetClone)
parent.removeChildNode(mytargetLyr)

mycensusLyr = root.findLayer(censusLyr.id())
censusClone = mycensusLyr.clone()
parent = mycensusLyr.parent()
parent.insertChildNode(1, censusClone)
parent.removeChildNode(mycensusLyr)

# Set properties for the join
targetField = 'CTUID'
inField = 'CTUID'
joinObject = QgsVectorJoinInfo()
joinObject.joinLayerId = censusLyr.id()
joinObject.joinFieldName = inField
joinObject.targetFieldName = targetField
print(targetLyr.addJoin(joinObject))  # You should get True as response.
targetLyr.addJoin(joinObject)

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
table.setVectorLayer(huff_model)
table.setMaximumNumberOfFeatures(huff_model.featureCount())
c.addItem(table)

# Checks for the existence of the file with the same name and removes it.
if os.path.isfile(PDF_file):
    os.remove(PDF_file)

printer = QPrinter()
printer.setOutputFormat(QPrinter.PdfFormat)
printer.setOutputFileName("C:/Users/Oski/Py_internship/Huff_Model_Oski/Outputs/out.pdf")
printer.setPaperSize(QSizeF(c.paperWidth(), c.paperHeight()), QPrinter.Millimeter)
printer.setFullPage(True)

pdfPainter = QPainter(printer)
paperRectMM = printer.pageRect(QPrinter.Millimeter)
paperRectPixel = printer.pageRect(QPrinter.DevicePixel)
c.render(pdfPainter, paperRectPixel, paperRectMM)
pdfPainter.end()





