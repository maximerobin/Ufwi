
"""
Copyright (C) 2009-2011 EdenWall Technologies

This file is part of NuFirewall. 
 
 NuFirewall is free software: you can redistribute it and/or modify 
 it under the terms of the GNU General Public License as published by 
 the Free Software Foundation, version 3 of the License. 
 
 NuFirewall is distributed in the hope that it will be useful, 
 but WITHOUT ANY WARRANTY; without even the implied warranty of 
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
 GNU General Public License for more details. 
 
 You should have received a copy of the GNU General Public License 
 along with NuFirewall.  If not, see <http://www.gnu.org/licenses/>
"""

from PyQt4.QtGui import QGraphicsScene, QPen, \
                        QBrush, QFont
from PyQt4.QtCore import Qt, SIGNAL

from ufwi_log.client.qt.args import arg_types
from ufwi_rpcd.common import tr
from ufwi_log.client.qt.views.baritem import BarItem
from ufwi_log.client.qt.views.pieitem import PieItem

class GraphicsScene(QGraphicsScene):

    SELECTABLE = 0
    UNSELECTABLE = 1
    POSITION = 2

    def __init__(self, parent):
        QGraphicsScene.__init__(self, parent)

        self.pen_selected = QPen()
        self.pen_selected.setWidth(3)

        self.pen_unselected = QPen()
        self.pen_unselected.setWidth(1)

        self.text_font = QFont()
        self.text_font.setPointSizeF(10)

        self.last_selected= None
        self.mousePress = False
        self.parent_view = parent
        self.compatibility = parent.user_settings.compatibility
        self.last_color= None

    def setTextSize(self, size):
        self.text_font.setPointSizeF(size)
    def getTextSize(self):
        return self.text_font.pointSizeF()

    textSize = property(getTextSize, setTextSize)

    def mouseDoubleClickEvent(self, mouseEvent):

        selected = self.itemAt(mouseEvent.scenePos())

        if selected and (isinstance(selected, BarItem) or isinstance(selected, PieItem)):
            item = self.selectItem(selected)

            if item:
                header = self.parent_view.my_model.horizontalHeaderItem(0).text()
                name = self.parent_view.arg_types[unicode(header)]
                types = arg_types[name]

                if len(types.pagelinks) > 0:
                    field = types.pagelinks[0]
                    pos = item.pos

                    label = unicode(self.parent_view.my_model.item(pos, 0).text())
                    value = label

                    if label != 'Other':
                        if 'username' in self.parent_view.result['columns'] and self.compatibility.user_id:
                            for row in range(len(self.parent_view.data)):
                                if unicode(self.parent_view.data[row][0][0]) == label:
                                    value = self.parent_view.data[row][0][1]
                                    break
                        if self.parent_view.cumulative_mode:
                            arg_data = self.parent_view.my_model.data(self.parent_view.my_model.index(pos, 0), Qt.UserRole).toPyObject()
                            field = field = unicode(self.parent_view.columns[0])
                            filters = self.parent_view.fetcher.getArgs()
                            args = arg_types[field].get_pagelink_args(field, arg_data)

                            for key, value in args.iteritems():
                                if key in filters:
                                    self.parent_view.emit(SIGNAL('add_filter'), key, value)
                                    return
                            if field in filters:
                                self.parent_view.emit(SIGNAL('add_filter'), field, value)
                            else:
                                self.parent_view.loadPage(field, arg_data.label, arg_data.value, pagename=None)
                        else:
                            self.parent_view.loadPage(field, label, value, pagename=None)


    def getTotalCount(self):
        total = 0
        for item in self.items():
            if isinstance(item, BarItem) or isinstance(item, PieItem):
                total = total + int(item.value)
        return int(total)

    def _setInfoArea(self, mouseEvent, selected):

        pos = selected.pos
        title = self.parent_view.my_model.horizontalHeaderItem(0).text()

        value = selected.value
        if self.parent_view.my_model.item(pos, 0):
            key = unicode(self.parent_view.my_model.item(pos, 0).text())
        else:
            key = ""
        unit = arg_types[self.parent_view.columns[1]].unit
        percent = value / self.getTotalCount() * 100

        if int(percent) == 0:
            percent = tr('less than 1')
        else:
            percent = '%i' % percent

        additional = u''
        try:
            sort_col = self.parent_view.columns.index(self.parent_view.result['args']['sortby'])
        except (KeyError, ValueError):
            pass
        else:
            # XXX 1 is an hardcoded value. For now, only the second column is
            # graphable (labelised by first column).
            # When it'll be possible to graph an other column, it must check
            # if sort_col is different than label column (first) and graphed
            # column.
            if sort_col > 1:


                label = tr(str(arg_types[self.parent_view.columns[sort_col]].label))
                data = self.parent_view.my_model.data(self.parent_view.my_model.index(selected.pos, sort_col))
                additional = "<b>%s</b>: %s" % (label, unicode(data.toString()))

        percent_text = tr("<b>%s %%</b> of: %s") % (percent, title)



        self.parent_view.info_area.setText("""
             <table>
             <tr style="vertical-align: top;">
             <td style="padding-left: 10px;" >
             <b>%s :</b> %s<br>
             <b>%s :</b>
             <ul>
             <li><b>%i</b> %s</li>
             <li>%s</li>
             %s
             </ul>
             </td>
             </tr>
             </table>""" % (title, key, tr("Statistics"), value, unit, percent_text,
                             '<li>%s</li>' % additional if additional else ''))


#        if hasattr(selected,'_val') and int(selected.data(self.SELECTABLE).toString()) != self.UNSELECTABLE:
        if hasattr(selected,'value'):# and int(selected.data(self.SELECTABLE).toString()) != self.UNSELECTABLE:
            selected.setToolTip('<b><u>%s</u></b><br /><b>%i</b> %s (%s)%s' % (key, value, unit, percent_text,
                                                      '<br />%s' % additional if additional else ''))

    def mousePressEvent(self, mouseEvent):
        if (mouseEvent.button() != Qt.LeftButton):
            return

        selected = self.itemAt(mouseEvent.scenePos())
        if selected and (isinstance(selected, BarItem) or isinstance(selected, PieItem)):
                self.selectItem(selected)
                self.unselected(selected)
                self.update(self.sceneRect())
        else:
            self.mousePress = True
        QGraphicsScene.mousePressEvent(self, mouseEvent)



    def mouseReleaseEvent(self, mouseEvent):
        if self.mousePress:
            self.mousePress = False


    def mouseMoveEvent(self, mouseEvent):
        selected = self.itemAt(mouseEvent.scenePos())
        last_selected = self.itemAt(mouseEvent.lastScenePos())

        update = False

        if last_selected and isinstance(last_selected, BarItem) or last_selected and isinstance(last_selected, PieItem):
            try:
                last_selected.setBrush(QBrush((last_selected.color)))
                update = True
            except Exception, err:
                # TODO
                pass

        if selected is None or (not isinstance(selected, PieItem) and not isinstance(selected, BarItem)):
            self.parent_view.setDragMode(self.parent_view.ScrollHandDrag)
            return
        else:
            self.parent_view.setDragMode(self.parent_view.NoDrag)

        if isinstance(selected, BarItem) or selected and isinstance(selected, PieItem):
            try:
                self._setInfoArea(mouseEvent, selected)
#                selected.setToolTip(self._initToolTip(treeitem))
                selected.setBrush(QBrush(selected.darkColor))
                self._setInfoArea(mouseEvent, selected)
                update = True
            except Exception, err:
                # TODO
                return
        if update:
            self.update(self.sceneRect())

    def initialColor(self):
        if self.last_color:
            item = self.last_color[0]
#            item = last_item
            color = self.last_color[1]
            item.setBrush(QBrush(color))
            self.last_color = None

    def selectItem(self, selected):
        if selected in self.items():
            if self.last_selected and self.last_selected == selected:
                selected.setPen(self.pen_unselected)
                selected.setSelected(False)
                self.last_selected = None
            else:
                selected.setPen(self.pen_selected)
                selected.setSelected(True)
                self.last_selected = selected
        return selected

    def unselected(self, selected):
        for item in self.items():
            if item != selected:
                if (isinstance(item, PieItem) or isinstance(item, BarItem) ):
                    item.setPen(self.pen_unselected)
                    item.setSelected(False)


