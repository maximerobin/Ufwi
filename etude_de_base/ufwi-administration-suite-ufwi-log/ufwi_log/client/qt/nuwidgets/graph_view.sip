class GraphView : QAbstractItemView
{
public:

%TypeHeaderCode
#include <graph_view.h>
%End
		GraphView(QWidget* parent = 0);
        virtual ~GraphView();

		void dataUpdated();

		bool isIndexHidden(const QModelIndex&) const;

		QRect itemRect(const QModelIndex&);

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
		int verticalOffset() const;
		int horizontalOffset() const;

		QRect visualRect(const QModelIndex& index) const;

		void printMe(QPainter& painter, QRect rect);

        void scrollTo(const QModelIndex&, QAbstractItemView::ScrollHint);
        void setSelection(const QRect&, QFlags<QItemSelectionModel::SelectionFlag>);
        QRegion visualRegionForSelection(const QItemSelection&) const;

		virtual void paint(QPainter& painter, QRect rect, QRect widget_size, bool draw_highlight) = 0;

private:
		QModelIndex moveCursor(QAbstractItemView::CursorAction, Qt::KeyboardModifiers);
};
