#pragma once

#include <QWidget>
#include <QPushButton>
#include <QColor>
#include <QPixmap>

class QLabel;
class QHBoxLayout;
class QVBoxLayout;

enum TextMode {
  None,
  Wrap,
  Detail
};

class LogItemWidget : public QWidget
{
    Q_OBJECT
public:
    explicit LogItemWidget(
        const QString& text,
        const QPixmap& image,
        const QColor& backgroundColor,
        const TextMode& textMode = TextMode::Wrap,
        const bool displayImage = true,
        QWidget* parent = nullptr);

    // Convenience overload if you want to create first, set later
    explicit LogItemWidget(const QColor& backgroundColor, QWidget* parent = nullptr);

    // API
    void setText(const QString& text);
    void setImage(const QPixmap& image);
    void clearImage();
    void setBackgroundColor(const QColor& color);
    void setMaximumImageSize(const QSize& sz);
    void setTextElideMode(Qt::TextElideMode mode); // default: Qt::ElideNone
    void setTextSelectable(bool selectable);       // default: true
    
    void setMaximumCharacters(int characters);

    // Layout & sizing
    // QSize sizeHint() const override;
    // QSize minimumSizeHint() const override;

protected:
    void paintEvent(QPaintEvent* e) override;
    void resizeEvent(QResizeEvent* e) override;

private:
    void initUi();
    void applyBackground();
    QPixmap scaledPixmapForLabel(const QPixmap& pm, const QSize& target) const;
    void updateElideWidth();

private:
    QColor        m_background;
    QLabel*       m_imageLabel {nullptr};
    QLabel*       m_textLabel  {nullptr};
    QHBoxLayout*  m_h_layout     {nullptr};
    QVBoxLayout*  m_v_layout     {nullptr};
    QSize         m_maxImgSize {320, 240};
    Qt::TextElideMode m_elide {Qt::ElideNone};


    QPushButton* showMoreBtn {nullptr};

    TextMode textMode_ {TextMode::None};
    bool displayImage_ {true};
    
    int maxCharacters_ {80};
    QString fullText_;
};

