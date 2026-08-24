#include "Files.h"
#include <QFile>
#include <QFileInfo>

namespace Files {

QString copyCueFile(const QString &originalBin, const QString &patchedBin)
{
    QFileInfo origInfo(originalBin);
    QString origCue = origInfo.path() + "/" + origInfo.completeBaseName() + ".cue";

    if (!QFile::exists(origCue))
        return {};

    QFileInfo patchedInfo(patchedBin);
    QString patchedCue = patchedInfo.path() + "/" + patchedInfo.completeBaseName() + ".cue";

    if (QFile::exists(patchedCue))
        QFile::remove(patchedCue);

    if (QFile::copy(origCue, patchedCue))
        return patchedCue;

    return {};
}

}