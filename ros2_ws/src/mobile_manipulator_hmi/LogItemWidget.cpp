#include "LogItemWidget.h"

#include <QHBoxLayout>
#include <QTextEdit>
#include <QLabel>
#include <QPalette>
#include <QPainter>
#include <QStyleOption>
#include <QMessageBox>
#include <QFontMetrics>
#include <QResizeEvent>

static QLabel* makeTextLabel(QWidget* parent) {
    auto* lbl = new QLabel(parent);
    lbl->setWordWrap(true);
    lbl->setTextInteractionFlags(Qt::TextSelectableByMouse | Qt::LinksAccessibleByMouse);
    lbl->setTextFormat(Qt::PlainText);
    // lbl->setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed);
    return lbl;
}

static QLabel* makeImageLabel(QWidget* parent) {
    auto* lbl = new QLabel(parent);
    lbl->setStyleSheet("background-color: yellow;");
    lbl->setSizePolicy(QSizePolicy::Fixed, QSizePolicy::Fixed);
    lbl->setAlignment(Qt::AlignCenter);
    return lbl;
}

LogItemWidget::LogItemWidget(const QString& text,
                             const QPixmap& image,
                             const QColor& backgroundColor,
                             const TextMode& textMode,
                             const bool displayImage,
                             QWidget* parent)
    : QWidget(parent), m_background(backgroundColor), textMode_(textMode), displayImage_(displayImage)
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
    m_textLabel->setWordWrap(true);

    m_h_layout = new QHBoxLayout(this);
    m_h_layout->setContentsMargins(10, 8, 10, 8);
    m_h_layout->setSpacing(10);
    m_v_layout = new QVBoxLayout();
    m_v_layout->setContentsMargins(10, 8, 10, 8);
    m_v_layout->addWidget(m_textLabel, /*stretch*/1);

    showMoreBtn = new QPushButton(tr("Show More"), this);
    showMoreBtn->setCursor(Qt::PointingHandCursor);
    showMoreBtn->setStyleSheet("font-size: 12px;");
    showMoreBtn->setVisible(false);


    // Connect button to show popup with full text
    connect(showMoreBtn, &QPushButton::clicked, this, [this]() {
       QDialog dialog(this);
       dialog.setWindowTitle(tr("Full Log Text"));
       dialog.resize(1200, 800);

       // --- Layout setup ---
       auto* mainLayout = new QVBoxLayout(&dialog);
       mainLayout->setContentsMargins(15, 15, 15, 15);
       mainLayout->setSpacing(10);

       // Container layout: text + image
       auto* topLayout = new QHBoxLayout();
       topLayout->setSpacing(10);

       // --- Text area ---
       auto* textEdit = new QTextEdit();
       textEdit->setReadOnly(true);
       textEdit->setWordWrapMode(QTextOption::WordWrap);
       textEdit->setAlignment(Qt::AlignJustify);  // <-- justify the text
       textEdit->setText(fullText_);

       // --- Optional image ---
       if (displayImage_ && m_imageLabel && !m_imageLabel->pixmap(Qt::ReturnByValue).isNull()) {
           auto* imgLabel = new QLabel();
           imgLabel->setPixmap(m_imageLabel->pixmap(Qt::ReturnByValue).scaledToWidth(480, Qt::SmoothTransformation));
           imgLabel->setAlignment(Qt::AlignTop | Qt::AlignRight);
           topLayout->addWidget(textEdit, /*stretch*/1);
           topLayout->addWidget(imgLabel);
       } else {
           topLayout->addWidget(textEdit);
       }

       mainLayout->addLayout(topLayout);
     
        // --- Button box ---
        auto* closeBtn = new QPushButton(tr("Close"));
        closeBtn->setFixedWidth(80);
        QObject::connect(closeBtn, &QPushButton::clicked, &dialog, &QDialog::accept);
        mainLayout->addWidget(closeBtn, 0, Qt::AlignRight);
     
        dialog.exec();
    });

    m_v_layout->addWidget(showMoreBtn);

    m_h_layout->addLayout(m_v_layout);

    // Give image a sensible fixed box; actual pixmap will be scaled into it
    if(displayImage_){
      m_imageLabel->setFixedSize(m_maxImgSize);
      m_h_layout->addWidget(m_imageLabel);
    }

    // Slightly nicer default font for logs
    QFont f = m_textLabel->font();
    f.setPointSizeF(f.pointSizeF() + 2.0);
    f.setWeight(QFont::Black);
    m_textLabel->setFont(f);
}

void LogItemWidget::applyBackground()
{
    // QPalette pal = palette();
    // pal.setColor(QPalette::Window, m_background);
    QString style = QString(
        //"background-color: %1;"
        "LogItemWidget { "
        "border: 5px solid %1;"
        "border-radius: 6px;"
        "}"
    ).arg(m_background.name());//, QColor(80, 80, 80).name()); // Example border color

    setStyleSheet(style);
    // setPalette(pal);
}

void LogItemWidget::setText(const QString& text)
{
    fullText_ = text;

    QString displayedText = text;
    if (text.length() > maxCharacters_) {
      if(textMode_ == TextMode::Wrap){
        displayedText = text.left(maxCharacters_ - 3) + "...";
      }
      else if(textMode_ == TextMode::Detail){
            displayedText = text.left(maxCharacters_ - 3) + "...";

            //// Create "Show More" button
            if(!showMoreBtn->isVisible()){
              showMoreBtn->setVisible(true);
            }

            //// Optional: position it beside or below the label
            //// (Assuming you have a layout containing m_textLabel)
            //if (auto layout = this->layout()) {
            //    layout->addWidget(showMoreBtn);
            //}

      }
    }else{
      showMoreBtn->setVisible(false);
    }

    m_textLabel->setText(displayedText);
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

// QSize LogItemWidget::sizeHint() const
// {
//     const int w = width() > 0 ? width() : 400;
//     // Estimate height based on text metrics and image box
//     const int textAreaWidth =
//         w - m_h_layout->contentsMargins().left()
//           - m_h_layout->contentsMargins().right()
//           - (m_imageLabel->isVisible() ? (m_imageLabel->width() + m_h_layout->spacing()) : 0);
// 
//     QFontMetrics fm(m_textLabel->font());
//     // Let QLabel do wrapping; we approximate rows by breaking on width
//     QString t = m_textLabel->text();
//     if (t.isEmpty()) t = " "; // avoid zero height
//     QRect br = fm.boundingRect(0, 0, std::max(50, textAreaWidth), 100000,
//                                Qt::TextWordWrap, t);
// 
//     const int hContent = std::max(br.height(), m_imageLabel->isVisible() ? m_maxImgSize.height() : 0);
//     const QMargins m = m_h_layout->contentsMargins();
//     const int h = hContent + m.top() + m.bottom();
// 
//     return { w, h };
// }
// 
// QSize LogItemWidget::minimumSizeHint() const
// {
//     return { 150, std::max(24, m_maxImgSize.height()) };
// }

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
    // updateElideWidth();

}

QPixmap LogItemWidget::scaledPixmapForLabel(const QPixmap& pm, const QSize& target) const
{
    if (pm.isNull() || !target.isValid()) return pm;
    Qt::TransformationMode mode = Qt::SmoothTransformation;
    return pm.scaled(target, Qt::KeepAspectRatio, mode);
}

void LogItemWidget::updateElideWidth()
{
  return;
    // if (m_elide == Qt::ElideNone) {
    //     m_textLabel->setWordWrap(true);
    //     return;
    // }

    // For eliding single-line text when space is tight.

    int textAreaWidth =
        width()
        - m_h_layout->contentsMargins().left()
        - m_h_layout->contentsMargins().right();
      
    if(displayImage_){
      textAreaWidth -= (m_imageLabel->isVisible() ? (m_imageLabel->width() + m_h_layout->spacing()) : 0);
    }

    m_textLabel->setFixedWidth(textAreaWidth);
    QFontMetrics fm(m_textLabel->font());
    const QString elided = fm.elidedText(m_textLabel->text(), m_elide, 80); // TODO: remove magic nr
    // Avoid flicker: only reset if changed
    if (elided != m_textLabel->text())
        m_textLabel->setText(elided);
}

void LogItemWidget::setMaximumCharacters(int characters){
  maxCharacters_ = characters;
}
