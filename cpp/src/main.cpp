#include <QApplication> 
#include "MainWindow.h"

int main(int argc, char *argv[])
{
    QApplication app(argc, argv);
    app.setApplicationName("xPatch");
    app.setApplicationVersion("0.1.25");
    app.setOrganizationName("JEJCo");
    MainWindow window;
    window.show();
    return app.exec();
}