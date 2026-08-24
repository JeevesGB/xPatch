#pragma once
#include <QWidget>
#include <QLineEdit>
#include <QPushButton>
#include <QProgressBar>
#include <QPlainTextEdit>
#include <QString>

class XDeltaRunner;

class MainWindow : public QWidget
{
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);

protected:
    void dragEnterEvent(QDragEnterEvent *event) override;
    void dropEvent(QDropEvent *event) override;

private slots:
    void setMode(const QString &mode);
    void browse(QLineEdit *edit);
    void run();
    void onFinished(int exitCode);
    void exportLog();
    void showHelp();
    void showAbout();

private:
    void initUi();
    void loadStylesheet();
    bool validate();

    QString mode = "create";
    QString outputPath;
    qint64 sourceSize = 0;

    QPushButton *createBtn;
    QPushButton *applyBtn;
    QPushButton *actionBtn;
    QLineEdit *origEdit;
    QLineEdit *modEdit;
    QLineEdit *patchEdit;
    QLineEdit *outputEdit;
    QProgressBar *progress;
    QPlainTextEdit *console;

    XDeltaRunner *runner = nullptr;
};