#include "XDeltaRunner.h"

XDeltaRunner::XDeltaRunner(const QString &executable, QObject *parent)
    : QObject(parent)
    , process(new QProcess(this))
{
    process->setProgram(executable);
    connect(process, &QProcess::readyReadStandardOutput, this, &XDeltaRunner::handleStdout);
    connect(process, &QProcess::readyReadStandardError, this, &XDeltaRunner::handleStderr);
    connect(process, QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, &XDeltaRunner::onFinished);
}

void XDeltaRunner::run(const QStringList &args)
{
    process->setArguments(args);
    emit outputReceived(QString("Running: xdelta3 %1\n").arg(args.join(' ')));
    process->start();
}

bool XDeltaRunner::isRunning() const
{
    return process->state() == QProcess::Running;
}

void XDeltaRunner::handleStdout()
{
    QString out = QString::fromUtf8(process->readAllStandardOutput()).trimmed();
    if (!out.isEmpty())
        emit outputReceived(out);
}

void XDeltaRunner::handleStderr()
{
    QString err = QString::fromUtf8(process->readAllStandardError()).trimmed();
    if (!err.isEmpty())
        emit outputReceived("ERROR: " + err);
}

void XDeltaRunner::onFinished(int exitCode, QProcess::ExitStatus)
{
    if (exitCode == 0)
        emit outputReceived("Process finished successfully.");
    else
        emit outputReceived(QString("Process failed with exit code: %1").arg(exitCode));
    emit finished(exitCode);
}