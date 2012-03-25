/*
 * Copyright(C) 2008 INL
 * Written by Romain Bignon <romain AT inl.fr>
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, version 3 of the License.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
 *
 * $Id$
 */

#ifndef GRAPH_VIEW
#define GRAPH_VIEW

#include <QWidget>
#include <QAbstractItemView>

class GraphView : public QAbstractItemView
{
	Q_OBJECT

protected:
	unsigned int validItems;
	static const char *colours[];

private:
	double totalValue;
	QModelIndex highlight;
	QModelIndex old_highlight;
	QFontMetrics fm;
	QRect selectionRect;
	QModelIndex moveCursor(QAbstractItemView::CursorAction, Qt::KeyboardModifiers) { return QModelIndex(); }

public:

	GraphView(QWidget* parent = 0);
	virtual ~GraphView() {}

	void dataUpdated();

	bool isIndexHidden(const QModelIndex&) const { return false; }

	QRect itemRect(const QModelIndex&) { return QRect(); }

	double getValueMax(unsigned int col = 1);

	double getValueMaxAll();

	double getValueMin(unsigned int col = 1);

	double getMeanValue(unsigned int col);

	void mouseReleaseEvent(QMouseEvent* event);
	void mouseMoveEvent(QMouseEvent* event);

	void paintEvent(QPaintEvent* event);

	unsigned int rows(const QModelIndex& index);

	void rowsInserted(const QModelIndex& parent, int start, int end);

	void rowsAboutToBeRemoved(const QModelIndex& parent, int start, int end);

	/* Qt > 4.2 wants this */
	int verticalOffset() const { return 0; }
	int horizontalOffset() const { return 0; }

	QRect visualRect(const QModelIndex& index) const;

	void printMe(QPainter& painter, QRect rect);

	void scrollTo(const QModelIndex&, QAbstractItemView::ScrollHint) {}
	void setSelection(const QRect&, QFlags<QItemSelectionModel::SelectionFlag>) {}
	QRegion visualRegionForSelection(const QItemSelection&) const { return QRegion(); }

	virtual void paint(QPainter& painter, QRect rect, QRect widget_size, bool draw_highlight) = 0;

};

#endif /* GRAPH_VIEW */
