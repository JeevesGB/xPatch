#include "MainWindow.h"
#include "XDeltaRunner.h"
#include "utils/Paths.h"
#include "utils/Files.h"
#include "utils/Checksum.h"

#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QGridLayout>
#include <QLabel>
#include <QFileDialog>
#include <QMessageBox>
#include <QDesktopServices>
#include <QUrl>
#include <QDragEnterEvent>
#include <QMimeData>
#include <QFileInfo>
#include <QDialog>
#include <QTextBrowser>
#include <QIcon>
#include <QFile>

static const QString VERSION = "0.1.25";

MainWindow::MainWindow(QWidget *parent)
    : QWidget(parent)
{
    setWindowTitle(QString("xPatch v%1").arg(VERSION));
    setWindowIcon(QIcon(Paths::resourcePath("ico.ico")));
    setMinimumSize(760, 620);
    setAcceptDrops(true);

    loadStylesheet();
    initUi();
    setMode("create");
}

void MainWindow::initUi()
{
    auto *layout = new QVBoxLayout(this);
    auto *grid = new QGridLayout;

    createBtn = new QPushButton("Create Patch");
    applyBtn  = new QPushButton("Apply Patch");
    createBtn->setObjectName("createPatchButton");
    applyBtn->setObjectName("applyPatchButton");
    createBtn->setCheckable(true);
    applyBtn->setCheckable(true);

    connect(createBtn, &QPushButton::clicked, this, [this]{ setMode("create"); });
    connect(applyBtn,  &QPushButton::clicked, this, [this]{ setMode("apply");  });

    auto *helpBtn  = new QPushButton("Help");
    auto *aboutBtn = new QPushButton("Version");
    helpBtn->setFixedWidth(55);
    connect(helpBtn,  &QPushButton::clicked, this, &MainWindow::showHelp);
    connect(aboutBtn, &QPushButton::clicked, this, &MainWindow::showAbout);

    auto *modeRow = new QHBoxLayout;
    modeRow->addWidget(createBtn);
    modeRow->addWidget(applyBtn);
    modeRow->addStretch();
    modeRow->addWidget(helpBtn);
    modeRow->addWidget(aboutBtn);
    grid->addLayout(modeRow, 0, 0, 1, 3);

    origEdit   = new QLineEdit;
    modEdit    = new QLineEdit;
    patchEdit  = new QLineEdit;
    outputEdit = new QLineEdit;

    struct Field { QString label; QLineEdit *edit; };
    QList<Field> fields = {
        {"Original BIN:", origEdit},
        {"Modified BIN:", modEdit},
        {"xDelta Patch:", patchEdit},
        {"Output BIN:",   outputEdit}
    };

    for (int i = 0; i < fields.size(); ++i) {
        auto *btn = new QPushButton("Browse");
        connect(btn, &QPushButton::clicked, this, [this, edit = fields[i].edit]{ browse(edit); });
        grid->addWidget(new QLabel(fields[i].label), i + 1, 0);
        grid->addWidget(fields[i].edit, i + 1, 1);
        grid->addWidget(btn, i + 1, 2);
    }

    actionBtn = new QPushButton("Create xDelta Patch");
    connect(actionBtn, &QPushButton::clicked, this, &MainWindow::run);
    grid->addWidget(actionBtn, 5, 0, 1, 3);

    layout->addLayout(grid);

    progress = new QProgressBar;
    layout->addWidget(progress);

    layout->addWidget(new QLabel("Console Output:"));
    console = new QPlainTextEdit;
    console->setReadOnly(true);
    layout->addWidget(console);

    auto *exportBtn = new QPushButton("Export Log");
    connect(exportBtn, &QPushButton::clicked, this, &MainWindow::exportLog);
    layout->addWidget(exportBtn);
}

void MainWindow::loadStylesheet()
{
    QString path = Paths::resourcePath("theme.qss");
    QFile f(path);
    if (f.open(QIODevice::ReadOnly | QIODevice::Text)) {
        setStyleSheet(QString::fromUtf8(f.readAll()));
    }
}

void MainWindow::setMode(const QString &m)
{
    mode = m;
    bool isCreate = (mode == "create");

    createBtn->setChecked(isCreate);
    applyBtn->setChecked(!isCreate);

    modEdit->setEnabled(isCreate);
    outputEdit->setEnabled(!isCreate);

    actionBtn->setText(isCreate ? "Create xDelta Patch" : "Apply Patch");
}

void MainWindow::dragEnterEvent(QDragEnterEvent *event)
{
    if (event->mimeData()->hasUrls())
        event->acceptProposedAction();
}

void MainWindow::dropEvent(QDropEvent *event)
{
    for (const QUrl &url : event->mimeData()->urls()) {
        QString path = url.toLocalFile();
        if (origEdit->text().isEmpty())
            origEdit->setText(path);
        else if (mode == "create" && modEdit->text().isEmpty())
            modEdit->setText(path);
        else if (patchEdit->text().isEmpty())
            patchEdit->setText(path);
    }
}

void MainWindow::browse(QLineEdit *edit)
{
    QString path;
    if (edit == patchEdit && mode == "create")
        path = QFileDialog::getSaveFileName(this, "Save Patch", "", "xDelta (*.xdelta)");
    else if (edit == outputEdit)
        path = QFileDialog::getSaveFileName(this, "Save Output", "", "BIN (*.bin)");
    else
        path = QFileDialog::getOpenFileName(this);

    if (!path.isEmpty())
        edit->setText(path);
}

bool MainWindow::validate()
{
    if (!QFileInfo::exists(origEdit->text())) {
        QMessageBox::critical(this, "Error", "Original file missing.");
        return false;
    }
    if (mode == "create") {
        if (!QFileInfo::exists(modEdit->text())) {
            QMessageBox::critical(this, "Error", "Modified file missing.");
            return false;
        }
        if (origEdit->text() == modEdit->text()) {
            QMessageBox::warning(this, "Error", "Original and Modified cannot match.");
            return false;
        }
    }
    return true;
}

void MainWindow::run()
{
    if (!validate())
        return;

    QString xdelta = Paths::findXdelta();
    if (xdelta.isEmpty()) {
        QMessageBox::critical(this, "Error", "xdelta3 not found.\nInstall it or place it in tool/");
        return;
    }

    if (runner && runner->isRunning())
        return;

    runner = new XDeltaRunner(xdelta, this);
    connect(runner, &XDeltaRunner::outputReceived, console, &QPlainTextEdit::appendPlainText);
    connect(runner, &XDeltaRunner::finished, this, &MainWindow::onFinished);

    console->clear();
    progress->setRange(0, 0); // indeterminate

    QStringList args;
    QString orig = origEdit->text();
    QString patch = patchEdit->text();

    if (mode == "create") {
        QString mod = modEdit->text();
        args = {"-e", "-s", orig, mod, patch};
        console->appendPlainText("Creating xDelta patch...");
        console->appendPlainText(QString("Original : %1 (%2 bytes)")
            .arg(QFileInfo(orig).fileName())
            .arg(QFileInfo(orig).size()));
        console->appendPlainText(QString("Modified : %1 (%2 bytes)")
            .arg(QFileInfo(mod).fileName())
            .arg(QFileInfo(mod).size()));
    } else {
        outputPath = outputEdit->text();
        sourceSize = QFileInfo(orig).size();
        args = {"-d", "-s", orig, patch, outputPath};
        console->appendPlainText("Applying xDelta patch...");
        console->appendPlainText(QString("Original : %1").arg(QFileInfo(orig).fileName()));
        console->appendPlainText(QString("Patch    : %1").arg(QFileInfo(patch).fileName()));
    }

    console->appendPlainText(QString(60, '-'));
    runner->run(args);
}

void MainWindow::onFinished(int exitCode)
{
    progress->setRange(0, 100);
    progress->setValue(100);

    if (exitCode != 0) {
        QMessageBox::critical(this, "Failed", "xdelta process failed.");
        return;
    }

    if (mode == "apply" && !outputPath.isEmpty()) {
        QString cue = Files::copyCueFile(origEdit->text(), outputPath);
        if (!cue.isEmpty())
            console->appendPlainText("CUE file copied to " + cue);
    }

    QMessageBox::information(this, "Success", "Operation completed.");

    if (!outputPath.isEmpty()) {
        QDesktopServices::openUrl(QUrl::fromLocalFile(QFileInfo(outputPath).absolutePath()));
    }
}

void MainWindow::exportLog()
{
    QString path = QFileDialog::getSaveFileName(this, "Save Log", "", "Text (*.txt)");
    if (!path.isEmpty()) {
        QFile f(path);
        if (f.open(QIODevice::WriteOnly | QIODevice::Text))
            f.write(console->toPlainText().toUtf8());
    }
}

void MainWindow::showHelp()
{
    QDialog dialog(this);
    dialog.setWindowTitle("xPatch Help");
    dialog.setMinimumSize(650, 550);

    auto *layout = new QVBoxLayout(&dialog);
    auto *browser = new QTextBrowser;
    browser->setOpenExternalLinks(true);
    browser->setHtml(QString(R"(
        <h2>xPatch v%1</h2>
        <h3><b>What This Tool Does</b></h3>
        Creates and applies xDelta patches for PlayStation 1 BIN files.
        <h3><b>Create Patch</b></h3>
        <ol>
        <li>Select ORIGINAL clean BIN</li>
        <li>Select MODIFIED BIN</li>
        <li>Choose patch save location</li>
        <li>Click Create</li>
        </ol>
        <h3><b>Apply Patch</b></h3>
        <ol>
        <li>Select ORIGINAL clean BIN</li>
        <li>Select .xdelta patch</li>
        <li>Choose output BIN name</li>
        <li>Click Apply</li>
        </ol>
        <h3><b>Checksum Verification</b></h3>
        It is strongly recommended to verify your original BIN checksum
        (MD5 or SHA1) before patching to ensure compatibility.
        Incorrect base files will cause patch failures.
        <h3><b>Resources</b></h3>
        <a href="https://github.com/jmacd/xdelta">xDelta Official GitHub</a>
        <h3><b>License</b></h3>
        This tool uses xdelta3. Please review its respective license.
        xPatch GUI is provided as-is without warranty.
    )").arg(VERSION));

    layout->addWidget(browser);
    auto *closeBtn = new QPushButton("Close");
    connect(closeBtn, &QPushButton::clicked, &dialog, &QDialog::accept);
    layout->addWidget(closeBtn);
    dialog.exec();
}

void MainWindow::showAbout()
{
    QDialog dialog(this);
    dialog.setWindowTitle("About xPatch");
    auto *layout = new QVBoxLayout(&dialog);
    auto *label = new QLabel(QString("<h2>xPatch</h2>Version %1<br>Developed by JeevesGB").arg(VERSION));
    label->setAlignment(Qt::AlignCenter);
    label->setTextFormat(Qt::RichText);
    layout->addWidget(label);
    auto *closeBtn = new QPushButton("Close");
    connect(closeBtn, &QPushButton::clicked, &dialog, &QDialog::accept);
    layout->addWidget(closeBtn);
    dialog.exec();
}