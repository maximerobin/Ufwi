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
#include <QDateTime>
#include <math.h>
#include <list>

#include "line_view.h"

class MeansSorter
{
public:

	bool operator() (std::pair<int, double>& i1, std::pair<int, double>& i2)
	{
		return i1.second > i2.second;
	}
};

LineView::LineView(QWidget* parent)
	: GraphXYView(parent)
{
}

QModelIndex LineView::indexAt(const QPoint& /* point */) const
{
	if(validItems == 0 || !this->model())
		return QModelIndex();

	return QModelIndex();
}

QRegion LineView::itemRegion(QModelIndex index)
{
	if(!index.isValid() || !this->model())
		return QRegion();

	return QRegion();

}

void LineView::paint(QPainter& painter, QRect rect, QRect widget_size, bool draw_highlight)
{
	GraphXYView::paint(painter, rect, widget_size, draw_highlight);

	if(!this->model())
		return;

	QStyleOptionViewItem option = this->viewOptions();

	QBrush background = option.palette.base();
	QPen foreground(option.palette.color(QPalette::Foreground));

	// Handle step by step size increment
	double step_width = floor(widget_size.width() / RESIZE_INCREMENT) * RESIZE_INCREMENT;
	double step_height = floor(widget_size.height() / RESIZE_INCREMENT) * RESIZE_INCREMENT;

	double value_max;
	double xmin, xmax;
	if(this->model()->rowCount(this->rootIndex()) != 0)
	{
		value_max = this->getValueMaxAll();
		xmin = this->getValueMin(0);
		xmax = this->getValueMax(0);
	}
	else
		return;

	// If there is no data yet, or the max is at 0, use a max of 10 to dispaly an axe
	if(value_max == 0.0)
		value_max = 10.0;

	if(xmin == xmax)
		return; // avoid division by 0;

	painter.save();

	// Offset to cerrectly center the graph after the resizing due to the step by step increment
	painter.translate((widget_size.width() - step_width) / 2.0, (widget_size.height() - step_height) / 2.0);

	painter.setPen(foreground);

	// Draw lines
	QFontMetrics fm(painter.font());
	int margin_size = fm.width("0");
	int x_axe_off = fm.width("0") * 5;

	// Order them by max mean value
	std::list<std::pair<int, double> > means;
	for(int col=1; col < this->model()->columnCount(this->rootIndex()); ++col)
		means.push_back(std::pair<int, double>(col, this->getMeanValue(col)));

	means.sort(MeansSorter());

	double width_max = 0.0;
	double height_max = 0.0;
	for(std::list<std::pair<int, double> >::iterator _col=means.begin(); _col != means.end(); ++_col)
	{
		int col = _col->first;
		QPolygon points;
		int keyNumber = 0;
		double x = 0.0;
		for(int row=0; row < this->model()->rowCount(this->rootIndex()); ++row)
		{

			QModelIndex index = this->model()->index(row, col, this->rootIndex());
			int value = index.data(Qt::UserRole).toInt();
			double x_value = this->model()->index(row, 0, this->rootIndex()).data(Qt::UserRole).toDouble();

			if(value >= 0.0)
			{
				width_max =  step_width - 2 * margin_size - x_axe_off;
				height_max = (step_height * (1.0 - TITLE_AREA)) - 2 * margin_size;

				double height = height_max * value/value_max;

				x = (double(x_value - xmin) / double(xmax - xmin)) * width_max;

				QColor color(this->colours[col]);
				color.setAlpha(200);

				//# Create the gradient effect
				QLinearGradient grad(QPointF(0.0, 0.0), QPointF(0.0, height_max));
				grad.setColorAt(1.0, color.dark(150));
				grad.setColorAt(0.95, color);
				grad.setColorAt(0.05, color);
				grad.setColorAt(0.0, Qt::white);

				painter.setBrush(QBrush(grad));

				points.append(QPoint(x + margin_size + x_axe_off, height_max - height + margin_size));
				keyNumber += 1;
			}
		}

		if(keyNumber != 0)
		{
			points.append(QPoint(x + margin_size + x_axe_off, height_max + margin_size));
			points.append(QPoint(margin_size + x_axe_off, height_max + margin_size));
		}
		painter.drawPolygon(points);
	}

	// Graduations
	double nbr_grad = xmax - xmin;
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
	if (dgrad < 1)
		dgrad = 1;

	double dx = (double(dgrad) / double(xmax-xmin)) * width_max;

	for(int i=0; (i * dgrad) <= xmax - xmin; ++i)
	{
		int grad_width = fm.width("0");
		painter.drawLine(margin_size + x_axe_off + (i*dx), height_max + margin_size, margin_size + x_axe_off + (i*dx), height_max + margin_size + grad_width);
		QString text = QString::number(int(dgrad * i));

		// Legend drawing:
		painter.translate(margin_size + x_axe_off + (i*dx), height_max + margin_size + 2*grad_width);
		painter.rotate(-45.0);
		int int_time = (i * dgrad) + xmin;
		QDateTime time = QDateTime::fromTime_t(int_time);
		text = time.toString(QString("h:mm:ss"));

		int txt_width = fm.width(text);
		painter.drawText(QRect(-txt_width, -dx, txt_width, 2*dx), Qt::AlignRight|Qt::AlignVCenter, text);
		painter.rotate(45.0);
		painter.translate(-(margin_size + x_axe_off + (i*dx)), -(height_max + margin_size + 2*grad_width));
	}

	painter.translate((step_width - widget_size.width()) / 2.0, (step_height - widget_size.height()) / 2.0);
	painter.restore();
}
