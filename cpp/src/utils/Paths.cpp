#include "Paths.h"
#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QStandardPaths>

namespace Paths {

QString resourcePath(const QString &relative)
{
    QString res = ":/" + relative;
    if (QFileInfo::exists(res))
        return res;

    QDir appDir(QCoreApplication::applicationDirPath());
    return appDir.filePath(relative);
}

QString findXdelta()
{
    QStringList candidates = {
        resourcePath("tool/xdelta3"),
        resourcePath("tool/xdelta3.exe"),
        QCoreApplication::applicationDirPath() + "/tool/xdelta3",
        QCoreApplication::applicationDirPath() + "/tool/xdelta3.exe"
    };

    for (const QString &c : candidates) {
        if (QFileInfo::exists(c) && QFileInfo(c).isExecutable())
            return c;
    }

    QString system = QStandardPaths::findExecutable("xdelta3");
    if (!system.isEmpty())
        return system;

    return {};
}

} 