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

#include <QPen>
#include <QPainter>
#include <math.h>
#include "graphxy_view.h"

GraphXYView::GraphXYView(QWidget* parent)
	: GraphView(parent),
	  margin(8),
	  totalSize(200),
	  histogramSize(totalSize - 2*margin)
{
}

void GraphXYView::paint(QPainter& painter, QRect rect, QRect widget_size, bool)
{
	if(!model())
		return;

	QStyleOptionViewItem option = this->viewOptions();

	QBrush background = option.palette.base();
	QPen foreground = QPen(option.palette.color(QPalette::Foreground));
	painter.save();
	painter.fillRect(rect, background);

	// Handle step by step size increment
	double step_width = floor(widget_size.width() / RESIZE_INCREMENT) * RESIZE_INCREMENT;
	double step_height = floor(widget_size.height() / RESIZE_INCREMENT) * RESIZE_INCREMENT;

	// Offset to correctly center the graph after the resizing due to the step by step increment
	painter.translate((widget_size.width() - step_width) / 2.0, (widget_size.height() - step_height) / 2.0);

	painter.setPen(foreground);
	QFontMetrics fm(painter.font());
	int margin_size = fm.width("0");
	int x_axe_off = fm.width("0") * 5;

	// Find the highest column
	double value_max;
	if(this->model()->rowCount(this->rootIndex()) > 1)
		value_max = this->getValueMax();
	else
		value_max = 0.0;

	// If there is no data yet, or the max is at 0, use a max of 10 to dispaly an axe
	if (value_max == 0)
		value_max = 10;

	double width_max =  step_width - (2 * margin_size) - x_axe_off;
	double height_max = (step_height * (1.0 - TITLE_AREA)) - 2 * margin_size;
	//double width = width_max / (this->model()->rowCount(this->rootIndex())+1);

	// Draw the horizontal axe
	painter.drawLine(margin_size + x_axe_off / 2, height_max + margin_size, step_width - margin_size, height_max + margin_size);

	// Draw the vertical axe
	painter.drawLine(margin_size  + x_axe_off, margin_size, margin_size + x_axe_off, height_max + margin_size);

	// Graduations
	double nbr_grad = value_max;
	int dgrad = 1;
	while(nbr_grad > 10)
	{
		nbr_grad = floor(nbr_grad / 10);
		dgrad = dgrad * 10;
	}

	if(nbr_grad <= 2)
	{
		dgrad = dgrad / 10;
		nbr_grad = 10;
	}

	// Prevent for infinite loops.
	if(dgrad < 1)
		dgrad = 1;

	double dy = double(dgrad) * height_max / value_max;
	int text_dy = fm.height();
	for(int i = 1; (i * dgrad) <= value_max; i++)
	{
		int y = height_max - (dy * i) + margin_size;
		int grad_width = fm.width("0");
		painter.drawLine(margin_size + x_axe_off - grad_width, y, margin_size + x_axe_off, y);
		QString text = QString::number(int(dgrad * i));
		painter.drawText(QRect(0, y - text_dy / 2.0, margin_size + x_axe_off - 2 * grad_width, text_dy), Qt::AlignRight|Qt::AlignVCenter, text);

		if(i % 2)
		{
			painter.setBrush(QColor(0, 255, 255, 64)); // Cyan
			painter.setPen(QPen(QColor(0, 0, 0, 0)));
			painter.drawRect(margin_size + x_axe_off, y, width_max, dy);
			painter.setPen(QPen(option.palette.color(QPalette::Foreground)));
		}
	}

	painter.translate((step_width - widget_size.width()) / 2.0, (step_height - widget_size.height()) / 2.0);
	painter.restore();
}
