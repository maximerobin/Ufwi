TEMPLATE        = lib
LANGUAGE        = C++
CONFIG          += qt warn_on release plugin
QMAKE_CLEAN     += libnuwidgets.so
QMAKE_CXXFLAGS  += -Wall -Werror -Wextra -Wno-unused-parameter
QMAKE_LIBS      += -lm

HEADERS         =       graph_view.h \
			graphxy_view.h \
			line_view.h

SOURCES         =       graph_view.cpp \
			graphxy_view.cpp \
			line_view.cpp

TARGET          = nuwidgets
PROJECTNAME     = nuwidgets

