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

#ifndef LINEVIEW_H
#define LINEVIEW_H

#include "graphxy_view.h"

class LineView : public GraphXYView
{
	static const int margin_size = 16;
	static const double TITLE_AREA = 0.2; // Ratio of the area where the title of the column is printed
	static const double COLUMN_SPACE_RATIO = 0.66; // Ratio of the size of one column and the size of the space between 2 columns
	static const int RESIZE_INCREMENT = 50;

public:

	LineView(QWidget* parent = 0);
	~LineView() {}

	QModelIndex indexAt(const QPoint& point) const;

	QRegion itemRegion(QModelIndex index);

	void paint(QPainter& painter, QRect rect, QRect widget_size, bool draw_highlight);

};

#endif /* LINEVIEW_H */
