class GraphXYView : GraphView
{
%TypeHeaderCode
#include "graphxy_view.h"
%End
public:

		GraphXYView(QWidget* parent = 0);
        virtual ~GraphXYView();

		virtual void paint(QPainter& painter, QRect rect, QRect widget_size, bool draw_highlight);
};

