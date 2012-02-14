class LineView : GraphXYView
{
%TypeHeaderCode
#include "line_view.h"
%End

public:

        LineView(QWidget* parent = 0);
        ~LineView();

        QModelIndex indexAt(const QPoint& point) const;

        QRegion itemRegion(QModelIndex index);

        void paint(QPainter& painter, QRect rect, QRect widget_size, bool draw_highlight);
};
