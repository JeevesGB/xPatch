#include "Checksum.h"
#include <QCryptographicHash>
#include <QFile>

namespace Checksum {

QString calculateHash(const QString &filePath, const QString &algorithm)
{
    QCryptographicHash::Algorithm algo = QCryptographicHash::Md5;
    if (algorithm.toLower() == "sha1")
        algo = QCryptographicHash::Sha1;
    else if (algorithm.toLower() == "sha256")
        algo = QCryptographicHash::Sha256;

    QFile file(filePath);
    if (!file.open(QIODevice::ReadOnly))
        return {};

    QCryptographicHash hash(algo);
    if (!hash.addData(&file))
        return {};

    return hash.result().toHex();
}

} 