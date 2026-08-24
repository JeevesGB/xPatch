#pragma once
#include <QString>

namespace Checksum {
    QString calculateHash(const QString &filePath, const QString &algorithm = "md5");
}