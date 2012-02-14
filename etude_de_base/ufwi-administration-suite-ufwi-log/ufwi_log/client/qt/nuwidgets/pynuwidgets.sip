%Module pynuwidgets 0

%Import QtCore/QtCoremod.sip
%Import QtGui/QtGuimod.sip
%If (Qt_4_2_0 -)

%Include graph_view.sip
%Include graphxy_view.sip
%Include line_view.sip

%End
