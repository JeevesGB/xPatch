#pragma once
#include <QObject>
#include <QProcess>
#include <QStringList>

class XDeltaRunner : public QObject
{
    Q_OBJECT
public:
    explicit XDeltaRunner(const QString &executable, QObject *parent = nullptr);

    void run(const QStringList &args);
    bool isRunning() const;

signals:
    void outputReceived(const QString &text);
    void finished(int exitCode);

private slots:
    void handleStdout();
    void handleStderr();
    void onFinished(int exitCode, QProcess::ExitStatus status);

private:
    QProcess *process;
};