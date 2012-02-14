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

#include <QScrollBar>
#include <QMouseEvent>
#include <QToolTip>
#include <QPainter>
#include "graph_view.h"

const char* GraphView::colours[] =  { "#21FF85", "#B2B6E0", "#5289FF", "#A9482E", "#C3F4F8", "#E5D587",
		   "#E07191", "#74D2F1", "#5BC466", "#92E0DF", "#FFFFFF", "#AFFF54",
		   "#C09858", "#FFCB75", "#33ADFF", "#9E4570", "#9AE0A1", "#47BE4F",
		   "#CC0099", "#E0DD8D", "#FF8A2B", "#4B5DFF", "#6DF8BE", "#9C56FF",
		   "#BE7344", "#CCBE78", "#E0ACD0", "#FF37E1", "#45709E", "#676FFF",
		   "#4CAC84", "#35FF1A", "#806170", "#C3BF46", "#E0829A", "#E6CBB7"};

GraphView::GraphView(QWidget* parent)
	: QAbstractItemView(parent),
	  validItems(1),
	  totalValue(0.0),
	  fm(QFont())
{
	horizontalScrollBar()->setRange(0, 0);
	verticalScrollBar()->setRange(0, 0);

	setMouseTracking(true);
}

void GraphView::dataUpdated()
{
	if(!this->model())
		return;

	this->validItems = 0;
	this->totalValue = 0.0;

	for (int row = 0; row < model()->rowCount(rootIndex()); ++row)
	{
		QModelIndex index = this->model()->index(row, 1, this->rootIndex());
		double value = this->model()->data(index, Qt::UserRole).toDouble();

		if(value > 0.0)
		{
			this->totalValue += value;
			this->validItems += 1;
		}
	}

	this->viewport()->update();
}

double GraphView::getValueMax(unsigned int col)
{
	double value_max = 0.0;
	for (int row = 0; row < model()->rowCount(rootIndex()); ++row)
	{
		QModelIndex index = this->model()->index(row, col, this->rootIndex());
		double value = this->model()->data(index, Qt::UserRole).toDouble();

		if(value > value_max)
			value_max = value;
	}

	return value_max;
}

double GraphView::getValueMaxAll()
{
	double value_max = 0.0;
	for (int row = 0; row < model()->rowCount(rootIndex()); ++row)
	{
		for(int col = 1; col < model()->columnCount(rootIndex()); ++col)
		{
			QModelIndex index = this->model()->index(row, col, this->rootIndex());
			double value = this->model()->data(index, Qt::UserRole).toDouble();

			if(value > value_max)
				value_max = value;
		}
	}

	return value_max;
}

double GraphView::getValueMin(unsigned int col)
{
	double value_min = 0.0;
	for (int row = 0; row < model()->rowCount(rootIndex()); ++row)
	{
		QModelIndex index = this->model()->index(row, col, this->rootIndex());
		double value = this->model()->data(index, Qt::UserRole).toDouble();

		if(value < value_min || row == 0)
			value_min = value;
	}

	return value_min;
}

double GraphView::getMeanValue(unsigned int col)
{
	double mean = 0.0;
	for (int row = 0; row < model()->rowCount(rootIndex()); ++row)
	{
		QModelIndex index = this->model()->index(row, col, this->rootIndex());
		double value = this->model()->data(index, Qt::UserRole).toDouble();

		mean += value;
	}
	mean /= model()->rowCount(rootIndex());

	return mean;
}

void GraphView::mouseReleaseEvent(QMouseEvent* event)
{
	QAbstractItemView::mouseReleaseEvent(event);
	this->selectionRect = QRect();
	this->viewport()->update();
}

void GraphView::mouseMoveEvent(QMouseEvent* event)
{
	if(!this->model())
		return;
	this->old_highlight = this->highlight;
	this->highlight = this->indexAt(event->pos());

	if(this->highlight != this->old_highlight)
	{
		if(this->highlight != QModelIndex())
			this->setToolTip(QString::number(this->model()->data(this->highlight, Qt::UserRole).toDouble()));
		else
			QToolTip::hideText();

		this->viewport()->update();
	}
}

void GraphView::paintEvent(QPaintEvent* event)
{
	QPainter painter(this->viewport());
	painter.setRenderHint(QPainter::Antialiasing);
	this->fm = QFontMetrics(painter.font());
	this->paint(painter, event->rect(), this->viewport()->rect(), true);
}

unsigned int GraphView::rows(const QModelIndex& index)
{
	if(!this->model())
		return 0;
	return this->model()->rowCount(this->model()->parent(index));
}

void GraphView::rowsInserted(const QModelIndex& parent, int start, int end)
{
	if(!model())
		return;
	for(int row = start; row <= end; ++row)
	{
		QModelIndex index = this->model()->index(row, 1, this->rootIndex());
		double value = this->model()->data(index, Qt::UserRole).toDouble();

		if(value > 0.0)
		{
			this->totalValue += value;
			this->validItems += 1;
		}
	}

	QAbstractItemView::rowsInserted(parent, start, end);
}

void GraphView::rowsAboutToBeRemoved(const QModelIndex& parent, int start, int end)
{
	if(!model())
		return;
	for(int row = start; row <= end; ++row)
	{
		QModelIndex index = this->model()->index(row, 1, this->rootIndex());
		double value = this->model()->data(index, Qt::UserRole).toDouble();

		if(value > 0.0)
		{
			this->totalValue -= value;
			this->validItems -= 1;
		}
	}

	QAbstractItemView::rowsAboutToBeRemoved(parent, start, end);
}

QRect GraphView::visualRect(const QModelIndex&) const
{
	return QRect(0, 0, this->viewport()->width(), this->viewport()->height());
}

void GraphView::printMe(QPainter& painter, QRect rect)
{
	painter.translate(rect.x(), rect.y());
	QRect widget_size(0, 0, rect.width(), rect.height());
	this->paint(painter, widget_size, widget_size, false);
	painter.translate(-rect.x(), -rect.y());
}
