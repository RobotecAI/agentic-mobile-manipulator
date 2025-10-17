#include "LogItemWidget.h"

#include <QHBoxLayout>
#include <QLabel>
#include <QPalette>
#include <QPainter>
#include <QStyleOption>
#include <QFontMetrics>
#include <QResizeEvent>

static QLabel* makeTextLabel(QWidget* parent) {
    auto* lbl = new QLabel(parent);
    lbl->setWordWrap(true);
    lbl->setTextInteractionFlags(Qt::TextSelectableByMouse | Qt::LinksAccessibleByMouse);
    lbl->setTextFormat(Qt::PlainText);
    lbl->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Preferred);
    return lbl;
}

static QLabel* makeImageLabel(QWidget* parent) {
    auto* lbl = new QLabel(parent);
    lbl->setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed);
    lbl->setAlignment(Qt::AlignCenter);
    return lbl;
}

LogItemWidget::LogItemWidget(const QString& text,
                             const QPixmap& image,
                             const QColor& backgroundColor,
                             QWidget* parent)
    : QWidget(parent), m_background(backgroundColor)
{
    initUi();
    setText(text);
    setImage(image);
    applyBackground();
}

LogItemWidget::LogItemWidget(const QColor& backgroundColor, QWidget* parent)
    : QWidget(parent), m_background(backgroundColor)
{
    initUi();
    applyBackground();
}

void LogItemWidget::initUi()
{
    setAttribute(Qt::WA_Hover, true);
    setAutoFillBackground(true);

    m_imageLabel = makeImageLabel(this);
    m_textLabel  = makeTextLabel(this);

    m_layout = new QHBoxLayout(this);
    m_layout->setContentsMargins(10, 8, 10, 8);
    m_layout->setSpacing(10);

    // Give image a sensible fixed box; actual pixmap will be scaled into it
    m_imageLabel->setFixedSize(m_maxImgSize);

    m_layout->addWidget(m_textLabel, /*stretch*/1);
    m_layout->addWidget(m_imageLabel);

    // Slightly nicer default font for logs
    QFont f = m_textLabel->font();
    f.setPointSizeF(f.pointSizeF() + 0.0);
    m_textLabel->setFont(f);
}

void LogItemWidget::applyBackground()
{
    QPalette pal = palette();
    pal.setColor(QPalette::Window, m_background);
    setPalette(pal);
}

void LogItemWidget::setText(const QString& text)
{
    m_textLabel->setText(text);
    updateElideWidth();
    updateGeometry();
}

void LogItemWidget::setImage(const QPixmap& image)
{
    if (image.isNull()) {
        clearImage();
        return;
    }
    const QPixmap scaled = scaledPixmapForLabel(image, m_maxImgSize);
    m_imageLabel->setPixmap(scaled);
    m_imageLabel->setVisible(true);
    updateGeometry();
}

void LogItemWidget::clearImage()
{
    m_imageLabel->clear();
    m_imageLabel->setVisible(false);
    updateGeometry();
}

void LogItemWidget::setBackgroundColor(const QColor& color)
{
    m_background = color;
    applyBackground();
    update();
}

void LogItemWidget::setMaximumImageSize(const QSize& sz)
{
    m_maxImgSize = sz.isValid() ? sz : QSize(32, 32);
    m_imageLabel->setFixedSize(m_maxImgSize);
    // Rescale if we already have a pixmap
    if (const QPixmap* pm = m_imageLabel->pixmap()) {
        if (!pm->isNull()) {
            setImage(*pm);
        }
    }
    updateGeometry();
}

void LogItemWidget::setTextElideMode(Qt::TextElideMode mode)
{
    m_elide = mode;
    updateElideWidth();
}

void LogItemWidget::setTextSelectable(bool selectable)
{
    auto flags = m_textLabel->textInteractionFlags();
    if (selectable)
        flags |= Qt::TextSelectableByMouse;
    else
        flags &= ~Qt::TextSelectableByMouse;
    m_textLabel->setTextInteractionFlags(flags);
}

QSize LogItemWidget::sizeHint() const
{
    const int w = width() > 0 ? width() : 400;
    // Estimate height based on text metrics and image box
    const int textAreaWidth =
        w - m_layout->contentsMargins().left()
          - m_layout->contentsMargins().right()
          - (m_imageLabel->isVisible() ? (m_imageLabel->width() + m_layout->spacing()) : 0);

    QFontMetrics fm(m_textLabel->font());
    // Let QLabel do wrapping; we approximate rows by breaking on width
    QString t = m_textLabel->text();
    if (t.isEmpty()) t = " "; // avoid zero height
    QRect br = fm.boundingRect(0, 0, std::max(50, textAreaWidth), 100000,
                               Qt::TextWordWrap, t);

    const int hContent = std::max(br.height(), m_imageLabel->isVisible() ? m_maxImgSize.height() : 0);
    const QMargins m = m_layout->contentsMargins();
    const int h = hContent + m.top() + m.bottom();

    return { w, h };
}

QSize LogItemWidget::minimumSizeHint() const
{
    return { 150, std::max(24, m_maxImgSize.height()) };
}

void LogItemWidget::paintEvent(QPaintEvent* e)
{
    Q_UNUSED(e);
    // Ensure style (and palette Window color) is painted correctly
    QStyleOption opt;
    opt.init(this);
    QPainter p(this);
    style()->drawPrimitive(QStyle::PE_Widget, &opt, &p, this);
}

void LogItemWidget::resizeEvent(QResizeEvent* e)
{
    QWidget::resizeEvent(e);
    updateElideWidth();
}

QPixmap LogItemWidget::scaledPixmapForLabel(const QPixmap& pm, const QSize& target) const
{
    if (pm.isNull() || !target.isValid()) return pm;
    Qt::TransformationMode mode = Qt::SmoothTransformation;
    return pm.scaled(target, Qt::KeepAspectRatio, mode);
}

void LogItemWidget::updateElideWidth()
{
    if (m_elide == Qt::ElideNone) {
        m_textLabel->setWordWrap(true);
        return;
    }

    // For eliding single-line text when space is tight.
    m_textLabel->setWordWrap(false);

    const int textAreaWidth =
        width()
        - m_layout->contentsMargins().left()
        - m_layout->contentsMargins().right()
        - (m_imageLabel->isVisible() ? (m_imageLabel->width() + m_layout->spacing()) : 0);

    QFontMetrics fm(m_textLabel->font());
    const QString elided = fm.elidedText(m_textLabel->text(), m_elide, std::max(30, textAreaWidth));
    // Avoid flicker: only reset if changed
    if (elided != m_textLabel->text())
        m_textLabel->setText(elided);
}

