<template>
  <div class="image-studio page-enter">
    <div class="app-shell">
      <header class="image-studio__header surface-card">
        <div>
          <div class="panel-overline">Image Studio</div>
          <h1>图片工作室</h1>
          <p>左侧管理图片，中间并排查看原图和处理图，右侧集中调整参数，不再来回切换和滑动页面。</p>
        </div>
        <div class="image-studio__header-meta">
          <span class="badge badge-primary">图片 {{ images.length }} 张</span>
          <span class="badge" :class="previewStateBadgeClass">{{ previewStateLabel }}</span>
          <button class="btn btn-ghost" :disabled="loadingImages" @click="fetchImages(true)">
            {{ loadingImages ? "刷新中..." : "刷新图片" }}
          </button>
        </div>
      </header>

      <div v-if="feedbackText" class="feedback-box image-studio__feedback" :class="feedbackType">
        {{ feedbackText }}
      </div>

      <section class="image-studio__workspace">
        <aside class="image-studio__sidebar">
          <section class="surface-card image-panel">
            <div class="panel-overline">Upload</div>
            <div class="image-panel__head">
              <div>
                <h2>上传图片</h2>
                <p>支持单张和多张批量上传，上传后自动绑定当前用户。</p>
              </div>
            </div>

            <label class="image-upload-dropzone">
              <input type="file" accept=".png,.jpg,.jpeg,.webp,.bmp" multiple @change="handleUpload" />
              <div class="image-upload-dropzone__icon">+</div>
              <strong>拖拽或点击上传图片</strong>
              <span>支持 PNG、JPG、JPEG、WEBP、BMP。</span>
            </label>
          </section>

          <section class="surface-card image-panel image-panel--fill">
            <div class="panel-overline">Library</div>
            <div class="image-panel__head">
              <div>
                <h2>图片列表</h2>
                <p>点击切换图片，中间画布和右侧参数会同步刷新。</p>
              </div>
            </div>

            <div v-if="loadingImages" class="empty-state compact-empty">
              <strong>图片加载中</strong>
              <span>正在同步你的图片工作区...</span>
            </div>

            <div v-else-if="images.length" class="image-list">
              <article
                v-for="item in images"
                :key="item.name"
                class="image-item"
                :class="{ active: selectedImage?.name === item.name }"
              >
                <button class="image-item__main" @click="selectImage(item.name)">
                  <div class="image-item__top">
                    <strong>{{ item.original_name }}</strong>
                    <span>{{ item.width }} × {{ item.height }}</span>
                  </div>
                  <div class="image-item__bottom">
                    {{ formatFileSize(item.size) }} · {{ formatDateTime(item.created_at) }}
                  </div>
                </button>
                <button class="btn btn-danger-soft image-item__delete" @click="deleteImage(item.name)">
                  删除
                </button>
              </article>
            </div>

            <div v-else class="empty-state compact-empty">
              <strong>还没有图片</strong>
              <span>先上传一张图片，开始你的图片工作流。</span>
            </div>
          </section>
        </aside>

        <main class="image-studio__canvas-column">
          <section class="surface-card image-canvas-panel">
            <div class="image-panel__head">
              <div>
                <div class="panel-overline">Canvas</div>
                <h2>处理预览</h2>
                <p>左边是原图，右边是处理后的预览，像双页文档一样并排对照。</p>
              </div>
              <div class="image-canvas-panel__meta">
                <span v-if="selectedImage" class="badge badge-success truncate-text">{{ selectedImage.original_name }}</span>
                <button class="btn btn-ghost" :disabled="runningOcr || !selectedImage" @click="runOcr">
                  {{ runningOcr ? "识别中..." : "OCR 识别当前画面" }}
                </button>
                <button class="btn btn-primary" :disabled="applyingProcess || !selectedImage" @click="applyProcessing">
                  {{ applyingProcess ? "保存中..." : "另存为新图片" }}
                </button>
              </div>
            </div>

            <div v-if="!selectedImage" class="empty-state image-canvas-empty">
              <strong>先选择一张图片</strong>
              <span>左侧上传或选择图片后，中间会固定显示原图和处理预览。</span>
            </div>

            <template v-else>
              <div class="image-canvas-grid">
                <article class="image-canvas-sheet">
                  <div class="image-canvas-sheet__head">
                    <strong>原图</strong>
                    <span>{{ selectedImage.width }} × {{ selectedImage.height }}</span>
                  </div>
                  <div class="image-preview-frame image-preview-frame--large">
                    <img
                      v-if="selectedImageUrl"
                      :src="selectedImageUrl"
                      alt="原图预览"
                      @click="openLightbox(selectedImageUrl, '原图', `${selectedImage.width} × ${selectedImage.height}`)"
                    />
                  </div>
                </article>

                <article class="image-canvas-sheet">
                  <div class="image-canvas-sheet__head">
                    <strong>处理预览</strong>
                    <span>{{ activePreviewSizeText || "等待预览" }}</span>
                  </div>
                  <div class="image-preview-frame image-preview-frame--large">
                    <img
                      v-if="processingPreview?.preview_data_url"
                      :src="processingPreview.preview_data_url"
                      alt="处理预览"
                      @click="openLightbox(processingPreview.preview_data_url, '处理预览', activePreviewSizeText || '处理后尺寸')"
                    />
                    <div v-else class="image-preview-frame__placeholder">
                      <strong>调右侧参数后会自动刷新这里</strong>
                      <span>系统会防抖同步预览，不需要每次手动点按钮。</span>
                    </div>
                  </div>
                </article>
              </div>

              <div v-if="activeQualityReport" class="image-quality-grid">
                <div class="quality-card">
                  <span class="quality-label">尺寸</span>
                  <strong class="quality-value">{{ activeQualityReport.width }} × {{ activeQualityReport.height }}</strong>
                </div>
                <div class="quality-card">
                  <span class="quality-label">亮度</span>
                  <strong class="quality-value">{{ activeQualityReport.brightness_score }}</strong>
                </div>
                <div class="quality-card">
                  <span class="quality-label">对比度</span>
                  <strong class="quality-value">{{ activeQualityReport.contrast_score }}</strong>
                </div>
                <div class="quality-card">
                  <span class="quality-label">清晰度</span>
                  <strong class="quality-value">{{ activeQualityReport.sharpness_score }}</strong>
                </div>
              </div>

              <div v-if="dominantColors.length" class="image-stage__color-strip">
                <div class="image-stage__color-head">
                  <strong>主色提取</strong>
                  <span>帮助快速判断图片整体色彩倾向</span>
                </div>
                <div class="image-stage__color-list">
                  <div v-for="color in dominantColors" :key="color.hex" class="image-stage__color-item">
                    <span class="image-stage__color-swatch" :style="{ backgroundColor: color.hex }"></span>
                    <strong>{{ color.hex }}</strong>
                    <small>{{ color.percentage }}%</small>
                  </div>
                </div>
              </div>

              <div v-if="activeQualityReport?.warnings?.length" class="image-warning-list">
                <strong>质量提醒</strong>
                <ul>
                  <li v-for="(item, index) in activeQualityReport.warnings" :key="`${item}-${index}`">
                    {{ item }}
                  </li>
                </ul>
              </div>
            </template>
          </section>

          <section class="surface-card image-results-panel">
            <div class="image-results-head">
              <div class="image-results-tabs">
                <button
                  v-for="tab in drawerTabs"
                  :key="tab.value"
                  type="button"
                  class="field-chip"
                  :class="{ active: activeDrawerTab === tab.value }"
                  @click="activeDrawerTab = tab.value"
                >
                  {{ tab.label }}
                </button>
              </div>
              <div class="image-results-actions compact">
                <button class="btn btn-ghost" :disabled="!ocrResult?.ocr_result?.full_text" @click="copyOcrText">
                  复制全文
                </button>
                <button class="btn btn-ghost" :disabled="!ocrResult?.ocr_result?.full_text" @click="exportOcrAsText">
                  导出文本
                </button>
                <button class="btn btn-ghost" :disabled="!ocrResult?.ocr_result?.structured_table?.length" @click="exportOcrAsCsv">
                  导出表格
                </button>
              </div>
            </div>

            <section v-show="activeDrawerTab === 'ocr'" class="image-results-body">
              <div class="image-results-title">
                <div>
                  <h2>OCR 识别结果</h2>
                  <p>默认先看重点摘要，全文和明细可按需展开，避免整段结果把页面拉太长。</p>
                </div>
              </div>

              <div v-if="runningOcr" class="empty-state">
                <strong>OCR 识别中</strong>
                <span>正在读取当前处理后的图片内容并识别文字，请稍候...</span>
              </div>

              <template v-else-if="ocrResult?.ocr_result">
                <div class="image-quality-grid">
                  <div class="quality-card">
                    <span class="quality-label">识别行数</span>
                    <strong class="quality-value">{{ ocrResult.ocr_result.line_count }}</strong>
                  </div>
                  <div class="quality-card">
                    <span class="quality-label">平均置信度</span>
                    <strong class="quality-value">{{ ocrResult.ocr_result.average_score }}</strong>
                  </div>
                  <div class="quality-card">
                    <span class="quality-label">检测耗时</span>
                    <strong class="quality-value">{{ ocrResult.ocr_result.elapsed?.[0] ?? "-" }}s</strong>
                  </div>
                  <div class="quality-card">
                    <span class="quality-label">识别耗时</span>
                    <strong class="quality-value">{{ ocrResult.ocr_result.elapsed?.[2] ?? "-" }}s</strong>
                  </div>
                </div>

                <div class="image-ocr-card">
                  <div class="image-panel__head image-ocr-card__head">
                    <div>
                      <strong>识别全文</strong>
                      <p>先显示精简版，方便快速扫读。</p>
                    </div>
                    <button
                      v-if="ocrResult.ocr_result.full_text && ocrResult.ocr_result.full_text.length > 320"
                      class="btn btn-ghost"
                      @click="showFullOcrText = !showFullOcrText"
                    >
                      {{ showFullOcrText ? "收起全文" : "展开全文" }}
                    </button>
                  </div>
                  <pre>{{ truncatedOcrText || "未识别到文字" }}</pre>
                </div>

                <div v-if="Object.keys(ocrResult.ocr_result.structured_fields || {}).length" class="image-ocr-card">
                  <strong>字段提取</strong>
                  <div class="image-ocr-kv-list">
                    <div v-for="(value, key) in ocrResult.ocr_result.structured_fields" :key="key" class="image-ocr-kv-item">
                      <span>{{ key }}</span>
                      <strong>{{ value }}</strong>
                    </div>
                  </div>
                </div>

                <div v-if="ocrResult.ocr_result.structured_table?.length" class="table-shell">
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th v-for="col in structuredTableColumns" :key="col">{{ col }}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(row, index) in structuredTablePreviewRows" :key="index">
                        <td v-for="col in structuredTableColumns" :key="col">{{ row[col] }}</td>
                      </tr>
                    </tbody>
                  </table>
                  <div v-if="structuredTableHiddenCount > 0" class="groupby-note subtle image-results-note">
                    <strong>结构化表格已精简展示</strong>
                    <span>当前只显示前 {{ structuredTablePreviewRows.length }} 行，其余 {{ structuredTableHiddenCount }} 行可通过导出 CSV 查看。</span>
                  </div>
                </div>

                <div v-if="ocrResult.ocr_result.blocks?.length" class="image-ocr-card">
                  <div class="image-panel__head image-ocr-card__head">
                    <div>
                      <strong>识别明细</strong>
                      <p>默认先展示前几条识别结果，避免列表过长。</p>
                    </div>
                    <button
                      v-if="ocrResult.ocr_result.blocks.length > 6"
                      class="btn btn-ghost"
                      @click="showAllOcrBlocks = !showAllOcrBlocks"
                    >
                      {{ showAllOcrBlocks ? "收起明细" : `展开全部 ${ocrResult.ocr_result.blocks.length} 条` }}
                    </button>
                  </div>
                  <div class="image-ocr-block-list">
                    <article v-for="(block, index) in displayedOcrBlocks" :key="`${block.text}-${index}`" class="image-ocr-block">
                      <div class="image-ocr-block__head">
                        <strong>第 {{ index + 1 }} 行</strong>
                        <span>置信度 {{ block.score }}</span>
                      </div>
                      <p>{{ block.text }}</p>
                    </article>
                  </div>
                </div>
              </template>

              <div v-else class="image-results-empty-state">
                <div class="image-results-empty-copy">
                  <strong>还没有 OCR 结果</strong>
                  <span>
                    {{
                      selectedImage
                        ? "当前图片已就绪，可以直接识别，也可以先同步预处理预览。"
                        : "先选择一张图片，结果区会同步显示识别摘要和导出入口。"
                    }}
                  </span>
                </div>

                <div class="image-results-quick-grid">
                  <article>
                    <span>当前图片</span>
                    <strong>{{ selectedImage?.original_name || "未选择" }}</strong>
                  </article>
                  <article>
                    <span>画面尺寸</span>
                    <strong>{{ activePreviewSizeText || "-" }}</strong>
                  </article>
                  <article>
                    <span>预览状态</span>
                    <strong>{{ previewStateLabel }}</strong>
                  </article>
                  <article>
                    <span>处理历史</span>
                    <strong>{{ imageHistory.length }} 条</strong>
                  </article>
                </div>

                <div class="image-results-empty-actions">
                  <button
                    type="button"
                    class="btn btn-ghost"
                    :disabled="loadingPreviewProcess || !selectedImage"
                    @click="runPreview({ silent: false })"
                  >
                    {{ loadingPreviewProcess ? "同步中..." : "同步预览" }}
                  </button>
                  <button
                    type="button"
                    class="btn btn-primary"
                    :disabled="runningOcr || !selectedImage"
                    @click="runOcr"
                  >
                    {{ runningOcr ? "识别中..." : "开始 OCR" }}
                  </button>
                  <button type="button" class="btn btn-ghost" @click="activeDrawerTab = 'history'">
                    查看历史
                  </button>
                </div>
              </div>
            </section>

            <section v-show="activeDrawerTab === 'history'" class="image-results-body">
              <div class="image-results-title">
                <div>
                  <h2>图片处理历史</h2>
                  <p>记录上传、保存处理结果、OCR 和导出轨迹，方便回看和回滚。</p>
                </div>
              </div>

              <div v-if="loadingHistory" class="empty-state">
                <strong>历史加载中</strong>
                <span>正在同步当前图片的处理记录...</span>
              </div>

              <div v-else-if="imageHistory.length" class="image-history-list">
                <article v-for="item in imageHistory" :key="item.id" class="image-history-item">
                  <div class="image-history-item__head">
                    <strong>{{ formatHistoryAction(item.action_type) }}</strong>
                    <span>{{ formatDateTime(item.created_at) }}</span>
                  </div>
                  <p>{{ item.operation_summary }}</p>
                  <div class="image-history-item__meta">
                    <span class="badge badge-soft">已导出：{{ item.exported ? "是" : "否" }}</span>
                    <span v-if="item.source_image_name" class="badge badge-soft">来源：{{ item.source_image_name }}</span>
                    <span v-if="item.result_image_name" class="badge badge-soft">结果：{{ item.result_image_name }}</span>
                    <span v-if="item.ocr_result?.line_count" class="badge badge-soft">OCR {{ item.ocr_result.line_count }} 行</span>
                  </div>
                  <div class="image-control-actions" v-if="item.action_type !== 'upload'">
                    <button
                      class="btn btn-ghost"
                      :disabled="rollingBackHistoryId === item.id"
                      @click="rollbackHistory(item.id)"
                    >
                      {{ rollingBackHistoryId === item.id ? "回滚中..." : "回滚为新图片" }}
                    </button>
                  </div>
                </article>
              </div>

              <div v-else class="image-results-empty-state">
                <div class="image-results-empty-copy">
                  <strong>还没有处理历史</strong>
                  <span>当前图片还没有可回看的处理轨迹，保存处理结果或执行 OCR 后会在这里沉淀记录。</span>
                </div>

                <div class="image-results-quick-grid">
                  <article>
                    <span>图片资产</span>
                    <strong>{{ images.length }} 张</strong>
                  </article>
                  <article>
                    <span>当前图片</span>
                    <strong>{{ selectedImage?.original_name || "未选择" }}</strong>
                  </article>
                  <article>
                    <span>预览状态</span>
                    <strong>{{ previewStateLabel }}</strong>
                  </article>
                  <article>
                    <span>OCR 状态</span>
                    <strong>{{ ocrResult?.ocr_result ? "已有结果" : "未识别" }}</strong>
                  </article>
                </div>

                <div class="image-results-empty-actions">
                  <button
                    type="button"
                    class="btn btn-ghost"
                    :disabled="loadingPreviewProcess || !selectedImage"
                    @click="runPreview({ silent: false })"
                  >
                    {{ loadingPreviewProcess ? "同步中..." : "同步预览" }}
                  </button>
                  <button
                    type="button"
                    class="btn btn-primary"
                    :disabled="applyingProcess || !selectedImage"
                    @click="applyProcessing"
                  >
                    {{ applyingProcess ? "保存中..." : "另存新图片" }}
                  </button>
                  <button type="button" class="btn btn-ghost" @click="activeDrawerTab = 'ocr'">
                    返回 OCR
                  </button>
                </div>
              </div>
            </section>
          </section>
        </main>

        <aside class="image-studio__controls">
          <section class="surface-card image-panel image-panel--sticky">
            <div class="panel-overline">Control Deck</div>
            <div class="image-panel__head">
              <div>
                <h2>预处理控制台</h2>
                <p>右侧集中调参数，调整后自动刷新预览，不需要频繁手动点按钮。</p>
              </div>
              <span class="badge" :class="previewStateBadgeClass">{{ previewStateLabel }}</span>
            </div>

            <div class="groupby-note subtle image-results-note">
              <strong>实时预览已开启</strong>
              <span>修改参数后，系统会自动防抖刷新处理预览。你仍然可以点击按钮立即强制同步。</span>
            </div>

            <details class="image-control-group" open>
              <summary>快捷预设</summary>
              <div class="image-control-group__body">
                <div class="image-preset-strip">
                  <button type="button" class="field-chip" @click="applyPreset('clarity')">灰度增强</button>
                  <button type="button" class="field-chip" @click="applyPreset('brighten')">提亮修复</button>
                  <button type="button" class="field-chip" @click="applyPreset('cover')">封面适配</button>
                  <button type="button" class="field-chip" @click="resetProcessingForm()">恢复默认</button>
                </div>
              </div>
            </details>

            <details class="image-control-group" open>
              <summary>基础变换</summary>
              <div class="image-control-group__body image-form-grid">
                <label class="inline-field checkbox-field">
                  <input v-model="processingForm.grayscale" type="checkbox" />
                  <span>灰度化</span>
                </label>
                <label class="inline-field checkbox-field">
                  <input v-model="processingForm.flipHorizontal" type="checkbox" />
                  <span>水平翻转</span>
                </label>
                <label class="inline-field checkbox-field">
                  <input v-model="processingForm.flipVertical" type="checkbox" />
                  <span>垂直翻转</span>
                </label>
                <label class="inline-field">
                  <span>旋转角度</span>
                  <input v-model.number="processingForm.rotateDegrees" type="number" min="-180" max="180" step="1" />
                </label>
              </div>
            </details>

            <details class="image-control-group">
              <summary>图像增强</summary>
              <div class="image-control-group__body image-form-grid">
                <label class="inline-field checkbox-field">
                  <input v-model="processingForm.denoise" type="checkbox" />
                  <span>去噪</span>
                </label>
                <label class="inline-field checkbox-field">
                  <input v-model="processingForm.sharpen" type="checkbox" />
                  <span>锐化增强</span>
                </label>
                <label class="inline-field">
                  <span>亮度</span>
                  <input v-model.number="processingForm.brightness" type="range" min="0.2" max="3" step="0.1" />
                  <small>{{ processingForm.brightness.toFixed(1) }} 倍</small>
                </label>
                <label class="inline-field">
                  <span>对比度</span>
                  <input v-model.number="processingForm.contrast" type="range" min="0.2" max="3" step="0.1" />
                  <small>{{ processingForm.contrast.toFixed(1) }} 倍</small>
                </label>
                <label class="inline-field">
                  <span>二值化阈值</span>
                  <input v-model.number="processingForm.binaryThreshold" type="number" min="0" max="255" placeholder="选填" />
                </label>
              </div>
            </details>

            <details class="image-control-group">
              <summary>裁剪与尺寸</summary>
              <div class="image-control-group__body image-form-grid">
                <label class="inline-field">
                  <span>裁剪起点 X</span>
                  <input v-model.number="processingForm.cropX" type="number" min="0" max="4096" placeholder="选填" />
                </label>
                <label class="inline-field">
                  <span>裁剪起点 Y</span>
                  <input v-model.number="processingForm.cropY" type="number" min="0" max="4096" placeholder="选填" />
                </label>
                <label class="inline-field">
                  <span>裁剪宽度</span>
                  <input v-model.number="processingForm.cropWidth" type="number" min="1" max="4096" placeholder="选填" />
                </label>
                <label class="inline-field">
                  <span>裁剪高度</span>
                  <input v-model.number="processingForm.cropHeight" type="number" min="1" max="4096" placeholder="选填" />
                </label>
                <label class="inline-field">
                  <span>目标宽度</span>
                  <input v-model.number="processingForm.targetWidth" type="number" min="1" max="4096" placeholder="选填" />
                </label>
                <label class="inline-field">
                  <span>目标高度</span>
                  <input v-model.number="processingForm.targetHeight" type="number" min="1" max="4096" placeholder="选填" />
                </label>
                <label class="inline-field checkbox-field">
                  <input v-model="processingForm.preserveAspect" type="checkbox" />
                  <span>等比缩放</span>
                </label>
              </div>
            </details>

            <details class="image-control-group" open>
              <summary>导出与执行</summary>
              <div class="image-control-group__body">
                <div class="image-form-grid">
                  <label class="inline-field">
                    <span>导出格式</span>
                    <select v-model="processingForm.outputFormat">
                      <option value="png">PNG</option>
                      <option value="jpg">JPG</option>
                      <option value="webp">WEBP</option>
                      <option value="bmp">BMP</option>
                    </select>
                  </label>
                </div>

                <div class="image-control-actions">
                  <button class="btn btn-ghost" :disabled="loadingPreviewProcess || !selectedImage" @click="runPreview({ silent: false })">
                    {{ loadingPreviewProcess ? "同步中..." : "立即同步预览" }}
                  </button>
                  <button class="btn btn-ghost" :disabled="runningOcr || !selectedImage" @click="runOcr">
                    {{ runningOcr ? "识别中..." : "OCR 识别当前画面" }}
                  </button>
                  <button class="btn btn-primary" :disabled="applyingProcess || !selectedImage" @click="applyProcessing">
                    {{ applyingProcess ? "保存中..." : "应用并另存新图片" }}
                  </button>
                </div>

                <div v-if="processingPreview?.operation_summary?.length" class="groupby-note subtle image-results-note">
                  <strong>当前处理摘要</strong>
                  <span>{{ processingPreview.operation_summary.join("、") }}</span>
                </div>
              </div>
            </details>
          </section>
        </aside>
      </section>
    </div>

    <div v-if="lightbox.visible" class="image-lightbox" @click.self="closeLightbox">
      <button type="button" class="image-lightbox__close" aria-label="关闭大图预览" @click="closeLightbox">
        ×
      </button>
      <div class="image-lightbox__content">
        <div class="image-lightbox__head">
          <strong>{{ lightbox.title }}</strong>
          <span>{{ lightbox.meta }}</span>
        </div>
        <div class="image-lightbox__frame">
          <img :src="lightbox.src" alt="大图预览" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import api from "../api";

const images = ref([]);
const selectedImage = ref(null);
const selectedImageUrl = ref("");
const selectedImageMeta = ref(null);
const processingPreview = ref(null);
const ocrResult = ref(null);
const imageHistory = ref([]);

const feedbackText = ref("");
const feedbackType = ref("success");

const loadingImages = ref(false);
const loadingSelectedImage = ref(false);
const loadingPreviewProcess = ref(false);
const applyingProcess = ref(false);
const runningOcr = ref(false);
const loadingHistory = ref(false);
const rollingBackHistoryId = ref(null);

const activeDrawerTab = ref("ocr");
const showFullOcrText = ref(false);
const showAllOcrBlocks = ref(false);
const previewState = ref("idle");
const previewSyncedAt = ref("");
const suppressAutoPreview = ref(false);
const lightbox = ref({
  visible: false,
  src: "",
  title: "",
  meta: "",
});

let previewTimer = null;
let previewRequestSerial = 0;

const processingForm = ref(createDefaultProcessingForm());

function createDefaultProcessingForm() {
  return {
    grayscale: false,
    binaryThreshold: null,
    rotateDegrees: 0,
    flipHorizontal: false,
    flipVertical: false,
    brightness: 1,
    contrast: 1,
    sharpen: false,
    denoise: false,
    cropX: null,
    cropY: null,
    cropWidth: null,
    cropHeight: null,
    targetWidth: null,
    targetHeight: null,
    preserveAspect: true,
    outputFormat: "png",
  };
}

const drawerTabs = [
  { value: "ocr", label: "OCR 结果" },
  { value: "history", label: "处理历史" },
];

const IMAGE_STICKY_TOP_OFFSET = 16;
const IMAGE_STICKY_MIN_TOP = 16;

const activePreviewUrl = computed(() => processingPreview.value?.preview_data_url || selectedImageUrl.value);
const activeQualityReport = computed(() => processingPreview.value?.quality_report || selectedImageMeta.value?.quality_report || null);
const dominantColors = computed(() => activeQualityReport.value?.dominant_colors || []);
const structuredTableColumns = computed(() => {
  const rows = ocrResult.value?.ocr_result?.structured_table || [];
  return rows.length ? Object.keys(rows[0]) : [];
});
const structuredTablePreviewRows = computed(() => {
  const rows = ocrResult.value?.ocr_result?.structured_table || [];
  return rows.slice(0, 8);
});
const structuredTableHiddenCount = computed(() => {
  const rows = ocrResult.value?.ocr_result?.structured_table || [];
  return Math.max(0, rows.length - structuredTablePreviewRows.value.length);
});
const displayedOcrBlocks = computed(() => {
  const blocks = ocrResult.value?.ocr_result?.blocks || [];
  return showAllOcrBlocks.value ? blocks : blocks.slice(0, 6);
});
const truncatedOcrText = computed(() => {
  const fullText = ocrResult.value?.ocr_result?.full_text || "";
  if (showFullOcrText.value || fullText.length <= 320) return fullText;
  return `${fullText.slice(0, 320)}...`;
});
const activePreviewSizeText = computed(() => {
  if (processingPreview.value?.preview_size) {
    return `${processingPreview.value.preview_size.width} × ${processingPreview.value.preview_size.height}`;
  }
  if (selectedImage.value) {
    return `${selectedImage.value.width} × ${selectedImage.value.height}`;
  }
  return "";
});
const previewStateLabel = computed(() => {
  if (loadingPreviewProcess.value || previewState.value === "syncing") return "预览同步中";
  if (previewState.value === "synced" && previewSyncedAt.value) return `已同步 · ${previewSyncedAt.value}`;
  if (previewState.value === "error") return "预览同步失败";
  return "等待调整";
});
const previewStateBadgeClass = computed(() => {
  if (loadingPreviewProcess.value || previewState.value === "syncing") return "badge-primary";
  if (previewState.value === "synced") return "badge-success";
  if (previewState.value === "error") return "badge-warning";
  return "badge-soft";
});
const processingPayloadSignature = computed(() => JSON.stringify(buildProcessingPayload()));

function revokeSelectedImageUrl() {
  if (selectedImageUrl.value?.startsWith("blob:")) {
    URL.revokeObjectURL(selectedImageUrl.value);
  }
  selectedImageUrl.value = "";
}

function openLightbox(src, title, meta = "") {
  if (!src) return;
  lightbox.value = {
    visible: true,
    src,
    title,
    meta,
  };
}

function closeLightbox() {
  lightbox.value = {
    visible: false,
    src: "",
    title: "",
    meta: "",
  };
}

function handleKeydown(event) {
  if (event.key === "Escape" && lightbox.value.visible) {
    closeLightbox();
  }
}

function syncImageStudioStickyMetrics() {
  const studioRoot = document.querySelector(".image-studio");
  if (!studioRoot) return;

  const topbar = document.querySelector(".platform-topbar");
  const topbarBottom = topbar?.getBoundingClientRect().bottom || 0;
  const sidebarTop = Math.max(IMAGE_STICKY_MIN_TOP, topbarBottom + IMAGE_STICKY_TOP_OFFSET);
  const sidebarMaxHeight = Math.max(360, window.innerHeight - sidebarTop - 24);

  studioRoot.style.setProperty("--image-sidebar-top", `${sidebarTop}px`);
  studioRoot.style.setProperty("--image-sidebar-max-height", `${sidebarMaxHeight}px`);
}

function handleStudioScroll() {
  syncImageStudioStickyMetrics();
}

function resetProcessingForm({ preserveFormat = true } = {}) {
  const nextFormat = preserveFormat ? processingForm.value.outputFormat : "png";
  suppressAutoPreview.value = true;
  processingForm.value = {
    ...createDefaultProcessingForm(),
    outputFormat: nextFormat,
  };
  processingPreview.value = null;
  ocrResult.value = null;
  showFullOcrText.value = false;
  showAllOcrBlocks.value = false;
  previewState.value = "idle";
  setTimeout(() => {
    suppressAutoPreview.value = false;
  }, 0);
}

function buildProcessingPayload() {
  return {
    grayscale: Boolean(processingForm.value.grayscale),
    binary_threshold:
      processingForm.value.binaryThreshold !== null && processingForm.value.binaryThreshold !== ""
        ? Number(processingForm.value.binaryThreshold)
        : null,
    rotate_degrees: Number(processingForm.value.rotateDegrees) || 0,
    flip_horizontal: Boolean(processingForm.value.flipHorizontal),
    flip_vertical: Boolean(processingForm.value.flipVertical),
    brightness: Number(processingForm.value.brightness) || 1,
    contrast: Number(processingForm.value.contrast) || 1,
    sharpen: Boolean(processingForm.value.sharpen),
    denoise: Boolean(processingForm.value.denoise),
    crop_x:
      processingForm.value.cropX !== null && processingForm.value.cropX !== ""
        ? Number(processingForm.value.cropX)
        : null,
    crop_y:
      processingForm.value.cropY !== null && processingForm.value.cropY !== ""
        ? Number(processingForm.value.cropY)
        : null,
    crop_width:
      processingForm.value.cropWidth !== null && processingForm.value.cropWidth !== ""
        ? Number(processingForm.value.cropWidth)
        : null,
    crop_height:
      processingForm.value.cropHeight !== null && processingForm.value.cropHeight !== ""
        ? Number(processingForm.value.cropHeight)
        : null,
    target_width: processingForm.value.targetWidth ? Number(processingForm.value.targetWidth) : null,
    target_height: processingForm.value.targetHeight ? Number(processingForm.value.targetHeight) : null,
    preserve_aspect: Boolean(processingForm.value.preserveAspect),
    output_format: processingForm.value.outputFormat,
  };
}

function formatFileSize(size) {
  const value = Number(size || 0);
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDateTime(value) {
  if (!value) return "-";
  try {
    return new Date(value).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return value;
  }
}

function formatHistoryAction(actionType) {
  return (
    {
      upload: "上传图片",
      process_save: "保存处理结果",
      ocr: "执行 OCR",
      rollback: "历史回滚",
    }[actionType] || actionType
  );
}

async function fetchImageBlobUrl(filename) {
  const res = await api.get(`/images/file/${encodeURIComponent(filename)}`, {
    responseType: "blob",
  });
  return URL.createObjectURL(res.data);
}

async function fetchImages(autoSelect = true) {
  loadingImages.value = true;
  try {
    const res = await api.get("/images");
    images.value = res.data?.images || [];

    if (!images.value.length) {
      selectedImage.value = null;
      selectedImageMeta.value = null;
      revokeSelectedImageUrl();
      processingPreview.value = null;
      ocrResult.value = null;
      imageHistory.value = [];
      return;
    }

    const currentStillExists = images.value.some((item) => item.name === selectedImage.value?.name);
    if (autoSelect && (!selectedImage.value || !currentStillExists)) {
      await selectImage(images.value[0].name);
    }
  } catch (error) {
    feedbackText.value = error.response?.data?.detail || "获取图片列表失败";
    feedbackType.value = "error";
  } finally {
    loadingImages.value = false;
  }
}

async function fetchImageHistory(filename = selectedImage.value?.name) {
  if (!filename) {
    imageHistory.value = [];
    return;
  }
  loadingHistory.value = true;
  try {
    const res = await api.get(`/images/history/${encodeURIComponent(filename)}`);
    imageHistory.value = res.data?.history || [];
  } catch {
    imageHistory.value = [];
  } finally {
    loadingHistory.value = false;
  }
}

async function selectImage(filename) {
  loadingSelectedImage.value = true;
  processingPreview.value = null;
  ocrResult.value = null;
  imageHistory.value = [];
  previewState.value = "idle";
  try {
    const [metaRes, blobUrl] = await Promise.all([
      api.get(`/images/meta/${encodeURIComponent(filename)}`),
      fetchImageBlobUrl(filename),
    ]);

    revokeSelectedImageUrl();
    selectedImageUrl.value = blobUrl;
    selectedImageMeta.value = metaRes.data;
    selectedImage.value = metaRes.data?.image || null;
    activeDrawerTab.value = "ocr";
    resetProcessingForm();
    await fetchImageHistory(filename);
    feedbackText.value = "";
  } catch (error) {
    feedbackText.value = error.response?.data?.detail || "加载图片失败";
    feedbackType.value = "error";
  } finally {
    loadingSelectedImage.value = false;
  }
}

async function handleUpload(event) {
  const files = Array.from(event.target.files || []);
  if (!files.length) return;

  try {
    let lastUploadedName = "";
    for (const file of files) {
      const formData = new FormData();
      formData.append("file", file);
      const res = await api.post("/images/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 120000,
      });
      lastUploadedName = res.data?.image?.name || lastUploadedName;
    }

    feedbackText.value = files.length > 1 ? `成功上传 ${files.length} 张图片` : "图片上传成功";
    feedbackType.value = "success";
    await fetchImages(false);
    if (lastUploadedName) {
      await selectImage(lastUploadedName);
    }
  } catch (error) {
    feedbackText.value = error.response?.data?.detail || "图片上传失败";
    feedbackType.value = "error";
  } finally {
    event.target.value = "";
  }
}

function queueAutoPreview() {
  if (!selectedImage.value || suppressAutoPreview.value) return;
  if (previewTimer) clearTimeout(previewTimer);
  previewState.value = "syncing";
  previewTimer = setTimeout(() => {
    runPreview({ silent: true });
  }, 450);
}

async function runPreview({ silent = false } = {}) {
  if (!selectedImage.value) {
    if (!silent) {
      feedbackText.value = "请先选择图片";
      feedbackType.value = "warning";
    }
    return;
  }

  const requestId = ++previewRequestSerial;
  previewState.value = "syncing";
  if (!silent) {
    loadingPreviewProcess.value = true;
  }

  try {
    const res = await api.post(
      `/images/process/preview/${encodeURIComponent(selectedImage.value.name)}`,
      buildProcessingPayload(),
      { timeout: 120000 }
    );

    if (requestId !== previewRequestSerial) return;

    processingPreview.value = res.data;
    previewState.value = "synced";
    previewSyncedAt.value = new Date().toLocaleTimeString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
    if (!silent) {
      feedbackText.value = "预览已同步";
      feedbackType.value = "success";
    }
  } catch (error) {
    if (requestId !== previewRequestSerial) return;
    previewState.value = "error";
    if (!silent || !processingPreview.value) {
      feedbackText.value = error.response?.data?.detail || "图片预处理预览失败";
      feedbackType.value = "error";
    }
  } finally {
    if (!silent && requestId === previewRequestSerial) {
      loadingPreviewProcess.value = false;
    }
  }
}

async function applyProcessing() {
  if (!selectedImage.value) {
    feedbackText.value = "请先选择图片";
    feedbackType.value = "warning";
    return;
  }

  applyingProcess.value = true;
  try {
    const res = await api.post(
      `/images/process/apply/${encodeURIComponent(selectedImage.value.name)}`,
      buildProcessingPayload(),
      { timeout: 120000 }
    );
    feedbackText.value = res.data?.msg || "图片处理完成";
    feedbackType.value = "success";
    await fetchImages(false);
    if (res.data?.image?.name) {
      await selectImage(res.data.image.name);
      activeDrawerTab.value = "history";
    }
  } catch (error) {
    feedbackText.value = error.response?.data?.detail || "图片处理保存失败";
    feedbackType.value = "error";
  } finally {
    applyingProcess.value = false;
  }
}

async function runOcr() {
  if (!selectedImage.value) {
    feedbackText.value = "请先选择图片";
    feedbackType.value = "warning";
    return;
  }

  runningOcr.value = true;
  activeDrawerTab.value = "ocr";
  try {
    const res = await api.post(
      `/images/ocr/${encodeURIComponent(selectedImage.value.name)}`,
      buildProcessingPayload(),
      { timeout: 120000 }
    );
    ocrResult.value = res.data;
    processingPreview.value = {
      preview_data_url: res.data?.preview_data_url,
      quality_report: res.data?.quality_report,
      operation_summary: res.data?.operation_summary || [],
      preview_size: {
        width: res.data?.quality_report?.width,
        height: res.data?.quality_report?.height,
      },
    };
    showFullOcrText.value = false;
    showAllOcrBlocks.value = false;
    feedbackText.value = res.data?.ocr_result?.line_count
      ? `OCR 识别完成，共识别 ${res.data.ocr_result.line_count} 行文本`
      : "OCR 识别完成，但未识别到清晰文本";
    feedbackType.value = "success";
    await fetchImageHistory(selectedImage.value.name);
  } catch (error) {
    feedbackText.value = error.response?.data?.detail || "OCR 识别失败";
    feedbackType.value = "error";
  } finally {
    runningOcr.value = false;
  }
}

async function deleteImage(filename) {
  try {
    const res = await api.delete(`/images/${encodeURIComponent(filename)}`);
    feedbackText.value = res.data?.msg || "图片删除成功";
    feedbackType.value = "success";
    const deletingCurrent = selectedImage.value?.name === filename;
    await fetchImages(!deletingCurrent);
    if (deletingCurrent && images.value.length) {
      await selectImage(images.value[0].name);
    }
    if (!images.value.length) {
      selectedImage.value = null;
      selectedImageMeta.value = null;
      revokeSelectedImageUrl();
      processingPreview.value = null;
      ocrResult.value = null;
      imageHistory.value = [];
    }
  } catch (error) {
    feedbackText.value = error.response?.data?.detail || "图片删除失败";
    feedbackType.value = "error";
  }
}

function applyPreset(preset) {
  if (preset === "clarity") {
    processingForm.value = {
      ...processingForm.value,
      grayscale: true,
      denoise: true,
      sharpen: true,
      contrast: 1.2,
      brightness: 1.0,
      binaryThreshold: 160,
    };
  } else if (preset === "brighten") {
    processingForm.value = {
      ...processingForm.value,
      grayscale: false,
      sharpen: false,
      brightness: 1.2,
      contrast: 1.1,
      binaryThreshold: null,
    };
  } else if (preset === "cover") {
    processingForm.value = {
      ...processingForm.value,
      targetWidth: 1280,
      targetHeight: 720,
      preserveAspect: true,
      rotateDegrees: 0,
      cropX: null,
      cropY: null,
      cropWidth: null,
      cropHeight: null,
    };
  }
  queueAutoPreview();
}

async function copyOcrText() {
  if (!ocrResult.value?.ocr_result?.full_text) return;
  try {
    await navigator.clipboard.writeText(ocrResult.value.ocr_result.full_text);
    feedbackText.value = "OCR 文本已复制";
    feedbackType.value = "success";
  } catch {
    feedbackText.value = "复制 OCR 文本失败";
    feedbackType.value = "error";
  }
}

function triggerBlobDownload(content, fileName, mimeType) {
  const blob = content instanceof Blob ? content : new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function markHistoryExported(historyId) {
  if (!historyId) return;
  try {
    await api.post(`/images/history/${historyId}/mark-exported`);
    await fetchImageHistory(selectedImage.value?.name);
  } catch {
    // export state update failure should not block user download
  }
}

async function exportOcrAsText() {
  if (!ocrResult.value?.ocr_result?.full_text) return;
  triggerBlobDownload(
    ocrResult.value.ocr_result.full_text,
    `${selectedImage.value?.original_name || "image"}_ocr.txt`,
    "text/plain;charset=utf-8"
  );
  feedbackText.value = "OCR 文本已导出";
  feedbackType.value = "success";
  await markHistoryExported(ocrResult.value?.history_id);
}

async function exportOcrAsCsv() {
  const rows = ocrResult.value?.ocr_result?.structured_table || [];
  if (!rows.length) return;
  const headers = Object.keys(rows[0]);
  const csvRows = [
    headers.join(","),
    ...rows.map((row) =>
      headers
        .map((header) => `"${String(row[header] ?? "").replace(/"/g, '""')}"`)
        .join(",")
    ),
  ];
  triggerBlobDownload(
    csvRows.join("\n"),
    `${selectedImage.value?.original_name || "image"}_structured.csv`,
    "text/csv;charset=utf-8"
  );
  feedbackText.value = "OCR 结构化表格已导出";
  feedbackType.value = "success";
  await markHistoryExported(ocrResult.value?.history_id);
}

async function rollbackHistory(historyId) {
  if (!historyId) return;
  rollingBackHistoryId.value = historyId;
  try {
    const res = await api.post(`/images/history/${historyId}/rollback`);
    feedbackText.value = res.data?.msg || "图片回滚完成";
    feedbackType.value = "success";
    await fetchImages(false);
    if (res.data?.image?.name) {
      await selectImage(res.data.image.name);
      activeDrawerTab.value = "history";
    }
  } catch (error) {
    feedbackText.value = error.response?.data?.detail || "图片回滚失败";
    feedbackType.value = "error";
  } finally {
    rollingBackHistoryId.value = null;
  }
}

watch(
  processingPayloadSignature,
  () => {
    queueAutoPreview();
  },
  { flush: "post" }
);

onMounted(async () => {
  await fetchImages(true);
  await nextTick();
  syncImageStudioStickyMetrics();
  window.addEventListener("resize", syncImageStudioStickyMetrics);
  window.addEventListener("scroll", handleStudioScroll, { passive: true });
  window.addEventListener("keydown", handleKeydown);
});

onBeforeUnmount(() => {
  revokeSelectedImageUrl();
  if (previewTimer) clearTimeout(previewTimer);
  window.removeEventListener("resize", syncImageStudioStickyMetrics);
  window.removeEventListener("scroll", handleStudioScroll);
  window.removeEventListener("keydown", handleKeydown);
});
</script>

<style scoped>
.image-studio {
  position: relative;
}

.image-studio .app-shell {
  width: 100%;
  min-height: auto;
  padding: 8px clamp(18px, 1.6vw, 24px) clamp(20px, 2vw, 28px);
}

.image-studio__header {
  margin-top: 0;
  padding: 22px 24px;
  border-radius: 26px;
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.image-studio__header h1 {
  margin: 0;
  font-size: clamp(30px, 4vw, 42px);
  line-height: 1.08;
  color: #0f172a;
}

.image-studio__header p {
  margin: 12px 0 0;
  color: #64748b;
  line-height: 1.8;
  max-width: 720px;
}

.image-studio__header-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
  align-items: center;
}

.image-studio__feedback {
  margin-top: 18px;
}

.image-studio__workspace {
  margin-top: 18px;
  display: grid;
  grid-template-columns: minmax(268px, 292px) minmax(0, 1fr) minmax(286px, 300px);
  gap: 18px;
  min-height: calc(100vh - 190px);
  align-items: start;
}

.image-studio__sidebar,
.image-studio__controls {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.image-studio__sidebar {
  position: sticky;
  top: var(--image-sidebar-top, 180px);
  align-self: start;
  width: auto;
  max-height: var(--image-sidebar-max-height, calc(100vh - 204px));
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  padding: 0 6px 6px 0;
}

.image-studio__controls {
  position: sticky;
  top: var(--image-sidebar-top, 180px);
  align-self: start;
  max-height: var(--image-sidebar-max-height, calc(100vh - 204px));
  min-width: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  padding: 0 6px 6px 0;
}

.image-studio__canvas-column {
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
  min-height: 0;
}

.image-panel {
  padding: 22px;
  border-radius: 24px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 251, 255, 0.92));
}

.image-panel--fill {
  min-height: 0;
  max-height: none;
  overflow: visible;
}

.image-panel--sticky {
  position: static;
  width: auto;
  max-height: none;
  overflow: visible;
}

.image-panel__head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.image-panel__head h2 {
  margin: 0;
  color: #0f172a;
  font-size: 24px;
}

.image-panel__head p {
  margin: 8px 0 0;
  color: #64748b;
  line-height: 1.75;
}

.image-upload-dropzone {
  padding: 24px;
  border-radius: 24px;
  border: 1px dashed rgba(91, 140, 255, 0.34);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(238, 246, 255, 0.9));
  display: grid;
  justify-items: center;
  gap: 10px;
  text-align: center;
  cursor: pointer;
}

.image-upload-dropzone input {
  display: none;
}

.image-upload-dropzone__icon {
  width: 58px;
  height: 58px;
  display: grid;
  place-items: center;
  border-radius: 18px;
  font-size: 28px;
  font-weight: 800;
  color: #2f64ff;
  background: rgba(255, 255, 255, 0.94);
  box-shadow: 0 12px 24px rgba(79, 140, 255, 0.14);
}

.image-upload-dropzone strong {
  color: #102445;
  font-size: 18px;
}

.image-upload-dropzone span {
  color: #6c7f99;
  line-height: 1.75;
}

.image-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.image-item {
  border-radius: 20px;
  border: 1px solid rgba(214, 226, 240, 0.92);
  background: rgba(255, 255, 255, 0.82);
  overflow: hidden;
}

.image-item.active {
  border-color: rgba(91, 140, 255, 0.42);
  box-shadow: 0 16px 28px rgba(91, 140, 255, 0.12);
}

.image-item__main {
  width: 100%;
  padding: 16px 18px;
  text-align: left;
}

.image-item__top {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.image-item__top strong {
  color: #102445;
  word-break: break-word;
}

.image-item__top span,
.image-item__bottom {
  color: #6d7f99;
  font-size: 13px;
  line-height: 1.7;
}

.image-item__delete {
  margin: 0 18px 16px;
}

.image-canvas-panel,
.image-results-panel {
  min-width: 0;
}

.image-canvas-panel,
.image-results-panel {
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.image-canvas-panel {
  padding: 20px;
}

.image-results-panel {
  align-self: start;
  min-height: 380px;
  padding: 18px 20px 20px;
}

.image-results-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: center;
  margin-bottom: 12px;
}

.image-canvas-panel__meta,
.image-results-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: flex-end;
  align-items: center;
}

.image-results-actions.compact .btn {
  height: 40px;
  padding: 0 14px;
  border-radius: 12px;
}

.field-chip {
  appearance: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  border: 1px solid #d8e3f2;
  border-radius: 999px;
  padding: 0 14px;
  color: #334155;
  background: linear-gradient(180deg, #ffffff, #f6f9fd);
  font-weight: 700;
  line-height: 1;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.06);
  transition:
    color 0.18s ease,
    background 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    transform 0.18s ease;
}

.field-chip:hover {
  transform: translateY(-1px);
  color: #1d4ed8;
  border-color: rgba(91, 140, 255, 0.38);
  box-shadow: 0 10px 22px rgba(59, 130, 246, 0.13);
}

.field-chip.active {
  color: #fff;
  border-color: transparent;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  box-shadow: 0 12px 24px rgba(59, 130, 246, 0.24);
}

.image-preset-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.image-preset-strip .field-chip {
  width: 100%;
  justify-content: center;
  box-shadow: none;
}

.image-canvas-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 16px;
}

.image-canvas-sheet {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.image-canvas-sheet__head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  color: #44566f;
  font-size: 14px;
}

.image-preview-frame {
  min-height: clamp(280px, 28vw, 430px);
  border-radius: 22px;
  border: 1px solid rgba(214, 226, 240, 0.92);
  background: linear-gradient(180deg, rgba(247, 251, 255, 0.98), rgba(240, 246, 255, 0.92));
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.image-preview-frame--large img {
  max-width: 100%;
  max-height: 620px;
  object-fit: contain;
  cursor: zoom-in;
}

.image-preview-frame__placeholder {
  padding: 20px;
  text-align: center;
  color: #64748b;
  line-height: 1.8;
}

.image-preview-frame__placeholder strong {
  display: block;
  color: #102445;
  margin-bottom: 8px;
}

.image-canvas-empty {
  min-height: 420px;
}

.image-quality-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.quality-card {
  min-width: 0;
  min-height: 96px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid #dde7f4;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(246, 250, 255, 0.96)),
    linear-gradient(135deg, rgba(59, 130, 246, 0.09), rgba(245, 158, 11, 0.05));
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.05);
}

.quality-label {
  display: block;
  margin-bottom: 10px;
  color: #475569;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.2;
}

.quality-value {
  display: block;
  color: #0f172a;
  font-size: clamp(20px, 2.4vw, 28px);
  line-height: 1.08;
  overflow-wrap: anywhere;
}

.image-stage__color-strip {
  padding: 14px 16px;
  border-radius: 20px;
  border: 1px solid rgba(91, 140, 255, 0.12);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(247, 251, 255, 0.92));
  margin-bottom: 18px;
}

.image-stage__color-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}

.image-stage__color-head strong {
  color: #102445;
}

.image-stage__color-head span {
  color: #6d7f99;
  font-size: 13px;
}

.image-stage__color-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.image-stage__color-item {
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(214, 226, 240, 0.92);
  display: flex;
  align-items: center;
  gap: 10px;
}

.image-stage__color-swatch {
  width: 18px;
  height: 18px;
  border-radius: 999px;
  border: 1px solid rgba(15, 23, 42, 0.1);
}

.image-stage__color-item strong {
  color: #102445;
  font-size: 13px;
}

.image-stage__color-item small {
  color: #6d7f99;
}

.image-warning-list {
  padding: 16px 18px;
  border-radius: 20px;
  background: rgba(255, 248, 238, 0.92);
  border: 1px solid rgba(255, 184, 77, 0.16);
  color: #875211;
}

.image-warning-list strong {
  display: block;
  margin-bottom: 8px;
}

.image-warning-list ul {
  margin: 0;
  padding-left: 18px;
  line-height: 1.8;
}

.image-results-tabs {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 0;
  padding: 4px;
  border-radius: 999px;
  background: #eef4fb;
  border: 1px solid #dce7f5;
}

.image-results-tabs .field-chip {
  min-height: 34px;
  border-color: transparent;
  background: transparent;
  box-shadow: none;
}

.image-results-tabs .field-chip:hover {
  background: rgba(255, 255, 255, 0.76);
  transform: none;
}

.image-results-tabs .field-chip.active {
  background: #ffffff;
  color: #102445;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.1);
}

.image-results-body {
  min-width: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  padding-right: 4px;
  max-height: 360px;
}

.image-results-title {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: 12px;
}

.image-results-title h2 {
  margin: 0;
  font-size: 22px;
  color: #0f172a;
}

.image-results-title p {
  margin: 6px 0 0;
  color: #64748b;
  line-height: 1.65;
}

.image-results-note {
  margin-top: 12px;
}

.image-results-empty-state {
  min-height: 252px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 18px;
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(214, 226, 240, 0.92);
  background:
    linear-gradient(180deg, rgba(248, 251, 255, 0.98), rgba(240, 246, 255, 0.92)),
    linear-gradient(135deg, rgba(91, 140, 255, 0.1), rgba(245, 158, 11, 0.08));
}

.image-results-empty-copy {
  display: grid;
  gap: 8px;
}

.image-results-empty-copy strong {
  color: #102445;
  font-size: 18px;
}

.image-results-empty-copy span {
  color: #64748b;
  line-height: 1.7;
}

.image-results-quick-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.image-results-quick-grid article {
  min-width: 0;
  min-height: 86px;
  padding: 13px 14px;
  border-radius: 16px;
  border: 1px solid rgba(214, 226, 240, 0.92);
  background: rgba(255, 255, 255, 0.78);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.image-results-quick-grid span {
  color: #6d7f99;
  font-size: 12px;
}

.image-results-quick-grid strong {
  color: #102445;
  font-size: 15px;
  overflow-wrap: anywhere;
}

.image-results-empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.image-ocr-card {
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid rgba(79, 140, 255, 0.12);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(247, 251, 255, 0.92));
  margin-bottom: 12px;
}

.image-ocr-card__head {
  margin-bottom: 12px;
}

.image-ocr-card strong {
  display: block;
  margin-bottom: 10px;
  color: #0f172a;
}

.image-ocr-card pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: "Cascadia Mono", "Consolas", monospace;
  color: #334a6c;
  line-height: 1.65;
  font-size: 13px;
}

.image-ocr-kv-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.image-ocr-kv-item {
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid rgba(214, 226, 240, 0.92);
  background: rgba(255, 255, 255, 0.82);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.image-ocr-kv-item span {
  font-size: 13px;
  color: #6d7f99;
}

.image-ocr-kv-item strong {
  color: #16325c;
  word-break: break-word;
}

.image-ocr-block-list {
  display: grid;
  gap: 12px;
}

.image-ocr-block {
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(214, 226, 240, 0.92);
  background: rgba(255, 255, 255, 0.82);
}

.image-ocr-block__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 8px;
}

.image-ocr-block__head strong {
  margin: 0;
}

.image-ocr-block__head span {
  font-size: 13px;
  color: #6d7f99;
}

.image-ocr-block p {
  margin: 0;
  color: #334a6c;
  line-height: 1.75;
}

.inline-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.inline-field > span {
  font-size: 14px;
  font-weight: 600;
  color: #334155;
}

.inline-field > small {
  color: #64748b;
  font-size: 12px;
  line-height: 1.6;
}

.inline-field input[type="number"],
.inline-field input[type="text"],
.inline-field select {
  width: 100%;
  min-width: 0;
  border: 1px solid #dbe3f0;
  background: rgba(248, 250, 252, 0.92);
  color: #0f172a;
  border-radius: 14px;
  padding: 12px 14px;
  outline: none;
  transition:
    border-color 0.2s ease,
    box-shadow 0.2s ease,
    background 0.2s ease;
}

.inline-field input[type="number"]:focus,
.inline-field input[type="text"]:focus,
.inline-field select:focus {
  border-color: rgba(91, 140, 255, 0.72);
  box-shadow: 0 0 0 4px rgba(91, 140, 255, 0.12);
  background: #fff;
}

.inline-field input[type="range"] {
  width: 100%;
}

.checkbox-field {
  flex-direction: row;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  min-height: 48px;
  padding: 11px 13px;
  border-radius: 14px;
  border: 1px solid rgba(214, 226, 240, 0.92);
  background: rgba(248, 250, 252, 0.92);
}

.checkbox-field input[type="checkbox"] {
  width: 18px;
  height: 18px;
  margin: 0;
}

.checkbox-field span {
  margin: 0;
  color: #334155;
  font-weight: 600;
}

.image-control-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.image-control-group {
  margin-top: 10px;
  border: 1px solid rgba(214, 226, 240, 0.92);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
  overflow: hidden;
}

.image-control-group summary {
  list-style: none;
  cursor: pointer;
  padding: 14px 16px;
  font-weight: 700;
  color: #102445;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.image-control-group summary::-webkit-details-marker {
  display: none;
}

.image-control-group summary::after {
  content: "展开";
  font-size: 12px;
  font-weight: 600;
  color: #6d7f99;
}

.image-control-group[open] summary {
  border-bottom: 1px solid rgba(214, 226, 240, 0.92);
  background: linear-gradient(180deg, rgba(247, 251, 255, 0.98), rgba(240, 246, 255, 0.92));
}

.image-control-group[open] summary::after {
  content: "收起";
}

.image-control-group__body {
  padding: 14px;
}

.image-control-group__body .image-form-grid,
.image-control-group__body .image-control-actions,
.image-control-group__body .groupby-note {
  margin-bottom: 0;
}

.image-history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.image-history-item {
  padding: 16px 18px;
  border-radius: 18px;
  border: 1px solid rgba(214, 226, 240, 0.92);
  background: rgba(255, 255, 255, 0.82);
}

.image-history-item__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  margin-bottom: 8px;
}

.image-history-item__head strong {
  color: #102445;
}

.image-history-item__head span {
  color: #6d7f99;
  font-size: 13px;
}

.image-history-item p {
  margin: 0 0 10px;
  color: #475569;
  line-height: 1.75;
}

.image-history-item__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.image-lightbox {
  position: fixed;
  inset: 0;
  z-index: 90;
  background: rgba(7, 12, 24, 0.82);
  backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.image-lightbox__content {
  width: min(1320px, 100%);
  max-height: calc(100vh - 48px);
  padding: 22px;
  border-radius: 28px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(244, 248, 255, 0.94));
  box-shadow: 0 28px 64px rgba(4, 10, 20, 0.35);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.image-lightbox__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  color: #102445;
}

.image-lightbox__head span {
  color: #6d7f99;
  font-size: 14px;
}

.image-lightbox__frame {
  flex: 1;
  min-height: 0;
  overflow: auto;
  border-radius: 20px;
  background: radial-gradient(circle at top, rgba(91, 140, 255, 0.08), rgba(15, 23, 42, 0.08));
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
}

.image-lightbox__frame img {
  max-width: 100%;
  max-height: calc(100vh - 170px);
  object-fit: contain;
}

.image-lightbox__close {
  position: absolute;
  top: 18px;
  right: 22px;
  width: 44px;
  height: 44px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  font-size: 26px;
  line-height: 1;
}

@media (max-width: 1500px) {
  .image-studio__workspace {
    display: grid;
    grid-template-columns: minmax(268px, 292px) minmax(0, 1fr);
    gap: 18px;
    min-height: auto;
  }

  .image-studio__controls {
    grid-column: 1 / -1;
    position: static;
    max-height: none;
    overflow: visible;
    padding: 0;
  }

  .image-studio__sidebar {
    position: static;
    max-height: none;
    overflow: visible;
    padding: 0;
    border: none;
    background: transparent;
    box-shadow: none;
  }

  .image-panel--sticky {
    position: static;
    max-height: none;
    overflow: visible;
  }

  .image-studio__canvas-column {
    display: flex;
    min-height: auto;
  }
}

@media (max-width: 1180px) {
  .image-studio__header,
  .image-studio__workspace,
  .image-canvas-grid,
  .image-quality-grid,
  .image-form-grid,
  .image-preset-strip,
  .image-ocr-kv-list,
  .image-results-quick-grid,
  .image-studio__hero-metrics {
    grid-template-columns: 1fr;
  }

  .image-studio__header {
    display: grid;
  }

  .image-panel--fill {
    max-height: none;
    overflow: visible;
  }

  .image-results-body {
    overflow: visible;
    padding-right: 0;
    max-height: none;
  }

  .image-results-panel {
    min-height: 0;
  }
}

@media (max-width: 760px) {
  .image-panel__head,
  .image-item__top,
  .image-stage__actions,
  .image-canvas-sheet__head,
  .image-stage__color-head,
  .image-history-item__head,
  .image-results-empty-actions,
  .image-results-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .image-control-actions .btn,
  .image-results-empty-actions .btn,
  .image-results-actions .btn,
  .image-item__delete {
    width: 100%;
  }

  .image-panel,
  .image-canvas-panel,
  .image-results-panel,
  .image-studio__header {
    padding: 22px;
  }

  .image-studio .app-shell {
    padding: 8px 14px 18px;
  }

  .image-lightbox {
    padding: 12px;
  }

  .image-lightbox__content {
    padding: 16px;
  }

  .image-lightbox__head {
    flex-direction: column;
    align-items: flex-start;
  }
}

.image-studio {
  color: #101828;
  background:
    radial-gradient(circle at 12% 5%, rgba(10, 132, 255, 0.14), transparent 28%),
    radial-gradient(circle at 92% 10%, rgba(52, 199, 89, 0.12), transparent 24%),
    radial-gradient(circle at 84% 86%, rgba(255, 122, 89, 0.1), transparent 30%),
    linear-gradient(135deg, #f9fbff 0%, #eef4f9 48%, #f8f4fb 100%);
}

.image-studio__header,
.image-panel,
.image-canvas-panel,
.image-results-panel,
.image-canvas-sheet,
.quality-card,
.image-stage__color-strip,
.image-warning-list,
.image-ocr-card,
.image-ocr-kv-item,
.image-ocr-block,
.image-history-item,
.image-results-quick-grid article {
  border-color: rgba(202, 214, 228, 0.62);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(250, 253, 255, 0.76)),
    rgba(255, 255, 255, 0.74);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.82),
    0 20px 48px rgba(35, 49, 73, 0.1);
  backdrop-filter: blur(24px) saturate(135%);
}

.image-studio__header,
.image-panel,
.image-canvas-panel,
.image-results-panel {
  border-radius: 28px;
}

.image-studio__header h1,
.image-panel__head h2,
.image-results-title h2,
.image-canvas-sheet__head strong,
.quality-value,
.image-stage__color-head strong,
.image-ocr-card strong,
.image-ocr-kv-item strong,
.image-history-item__head strong,
.image-results-empty-copy strong {
  color: #101828;
}

.image-studio__header p,
.image-panel__head p,
.image-upload-dropzone span,
.image-item__top span,
.image-item__bottom,
.quality-label,
.image-stage__color-head span,
.image-stage__color-item small,
.image-results-title p,
.image-results-empty-copy span,
.image-history-item p,
.image-history-item__meta {
  color: #64748b;
}

.panel-overline {
  color: #0a84ff;
}

.image-upload-dropzone,
.image-item,
.field-chip,
.image-preview-frame,
.image-results-note,
.inline-field input[type="number"],
.inline-field input[type="text"],
.inline-field select,
.image-control-group,
.image-results-empty-state {
  border-color: rgba(202, 214, 228, 0.62);
  background: rgba(255, 255, 255, 0.66);
  color: #263548;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.74);
}

.image-upload-dropzone,
.image-item,
.field-chip,
.image-preview-frame,
.quality-card,
.image-stage__color-strip,
.image-warning-list,
.image-ocr-card,
.image-control-group,
.image-history-item,
.image-results-quick-grid article {
  border-radius: 22px;
}

.image-upload-dropzone:hover,
.image-item:hover,
.field-chip:hover,
.field-chip.active,
.image-control-group[open] summary {
  border-color: rgba(10, 132, 255, 0.24);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 16px 34px rgba(35, 49, 73, 0.1);
}

.image-item.active,
.field-chip.active {
  border-color: rgba(10, 132, 255, 0.28);
  background: rgba(10, 132, 255, 0.09);
}

.image-upload-dropzone__icon {
  color: #ffffff;
  background: linear-gradient(135deg, #0a84ff, #34c759);
  box-shadow: 0 14px 32px rgba(10, 132, 255, 0.22);
}

.image-preview-frame {
  background:
    linear-gradient(135deg, rgba(10, 132, 255, 0.05), rgba(52, 199, 89, 0.04)),
    rgba(255, 255, 255, 0.54);
}

.image-control-group summary,
.image-results-tabs .field-chip.active {
  color: #075bb5;
}

.inline-field input[type="number"]:focus,
.inline-field input[type="text"]:focus,
.inline-field select:focus {
  border-color: rgba(10, 132, 255, 0.48);
  box-shadow: 0 0 0 5px rgba(10, 132, 255, 0.12);
}

.image-lightbox {
  background: rgba(15, 23, 42, 0.32);
  backdrop-filter: blur(16px);
}

.image-lightbox__content {
  border-color: rgba(255, 255, 255, 0.72);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.88);
}
</style>
