#pragma once

#include <QDialog>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QTextEdit>
#include <QPushButton>
#include <QLabel>
#include <QProcess>
class TaskDialog : public QDialog
{
    Q_OBJECT

public:
    explicit TaskDialog(QWidget *parent = nullptr);
    ~TaskDialog();
    QString getTaskText() const;

private slots:
    void onSendClicked();
    void onCancelClicked();
    void showOnScreenKeyboard();
    void hideOnScreenKeyboard();

private:
    QTextEdit *textEdit_;
    QPushButton *sendButton_;
    QPushButton *cancelButton_;
    QProcess *onScreenKeyboardProcess_ = nullptr;
};