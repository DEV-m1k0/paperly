/**
 * EasyMDE wiring для blog content в админке.
 *
 * Архитектура:
 * - На каждый `<textarea class="markdown-editor">` ищем родителя
 *   `.markdown-editor-wrap` и тянем оттуда data-upload-url / data-preview-url.
 * - Кастомные тулбар-кнопки:
 *     • [!] callouts (info/tip/warning/danger)
 *     • ▶ video-эмбед (вставляет @[youtube](ID))
 *     • Таблица 3×3
 *     • Code block с языком
 * - Drag-n-drop / paste картинок: перехватываем event'ы CodeMirror,
 *   читаем File, шлём на upload_url, в позицию курсора вставляем
 *   ![alt](url).
 * - CSRF: тянем cookie `csrftoken` (Django ставит его на admin-страницах).
 */
(function () {
  'use strict';

  if (typeof window.EasyMDE === 'undefined') {
    console.warn('[markdown-editor] EasyMDE not loaded — falling back to plain textarea');
    return;
  }

  function getCookie(name) {
    var m = document.cookie.match(new RegExp('(?:^|;\\s*)' + name + '=([^;]+)'));
    return m ? decodeURIComponent(m[1]) : '';
  }

  function uploadImage(file, uploadUrl) {
    var fd = new FormData();
    fd.append('image', file);
    return fetch(uploadUrl, {
      method: 'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken') },
      body: fd,
      credentials: 'same-origin',
    }).then(function (r) {
      if (!r.ok) throw new Error('upload failed: ' + r.status);
      return r.json();
    });
  }

  function insertAtCursor(editor, text) {
    var cm = editor.codemirror;
    var doc = cm.getDoc();
    doc.replaceSelection(text);
    cm.focus();
  }

  function makeCalloutAction(type) {
    return function (editor) {
      var label = {
        info: 'INFO', tip: 'TIP', note: 'NOTE',
        warning: 'WARNING', danger: 'DANGER', success: 'SUCCESS',
      }[type];
      var snippet =
        '\n> [!' + label + '] Заголовок\n' +
        '> Текст подсказки. Поддерживается **markdown**.\n\n';
      insertAtCursor(editor, snippet);
    };
  }

  function videoAction(editor) {
    var url = window.prompt('YouTube URL или ID:');
    if (!url) return;
    var m = url.match(/(?:youtu\.be\/|v=|embed\/)([\w\-]{6,})/);
    var vid = m ? m[1] : url.trim();
    insertAtCursor(editor, '\n@[youtube](' + vid + ')\n\n');
  }

  function tableAction(editor) {
    var snippet =
      '\n| Колонка 1 | Колонка 2 | Колонка 3 |\n' +
      '|---|---|---|\n' +
      '| Значение | Значение | Значение |\n' +
      '| Значение | Значение | Значение |\n\n';
    insertAtCursor(editor, snippet);
  }

  function codeBlockAction(editor) {
    var lang = window.prompt('Язык (python, js, html, bash, …):', 'python') || '';
    var snippet = '\n```' + lang + '\n# код\n```\n\n';
    insertAtCursor(editor, snippet);
  }

  function initEditor(textarea) {
    if (textarea.dataset.mdeInited) return;
    textarea.dataset.mdeInited = '1';

    var wrap = textarea.closest('.markdown-editor-wrap');
    var uploadUrl = wrap ? wrap.dataset.uploadUrl : '';
    var previewUrl = wrap ? wrap.dataset.previewUrl : '';

    var mde = new EasyMDE({
      element: textarea,
      autoDownloadFontAwesome: true,
      spellChecker: false,
      autofocus: false,
      forceSync: true,
      minHeight: '420px',
      placeholder: '# Заголовок статьи\n\nНачните писать в Markdown…',
      status: ['lines', 'words', 'cursor'],
      indentWithTabs: false,
      tabSize: 2,
      lineWrapping: true,
      previewClass: ['editor-preview', 'blog-prose'],
      toolbar: [
        'bold', 'italic', 'strikethrough', 'heading-1', 'heading-2', 'heading-3',
        '|', 'unordered-list', 'ordered-list', 'quote', 'horizontal-rule',
        '|', 'link', 'image',
        {
          name: 'table',
          action: tableAction,
          className: 'fa fa-table',
          title: 'Таблица',
        },
        {
          name: 'code',
          action: codeBlockAction,
          className: 'fa fa-code',
          title: 'Блок кода с языком',
        },
        '|',
        {
          name: 'callout-info',
          action: makeCalloutAction('info'),
          className: 'fa fa-info-circle',
          title: 'Callout: Info',
        },
        {
          name: 'callout-tip',
          action: makeCalloutAction('tip'),
          className: 'fa fa-lightbulb',
          title: 'Callout: Tip',
        },
        {
          name: 'callout-warning',
          action: makeCalloutAction('warning'),
          className: 'fa fa-exclamation-triangle',
          title: 'Callout: Warning',
        },
        {
          name: 'callout-danger',
          action: makeCalloutAction('danger'),
          className: 'fa fa-times-circle',
          title: 'Callout: Danger',
        },
        {
          name: 'video',
          action: videoAction,
          className: 'fa fa-play-circle',
          title: 'YouTube embed',
        },
        '|', 'preview', 'side-by-side', 'fullscreen', '|', 'guide',
      ],
      // Используем серверный рендер для preview — точное соответствие сайту.
      previewRender: function (plainText, previewElement) {
        if (!previewUrl) {
          // Fallback на встроенный рендер
          return EasyMDE.prototype.markdown(plainText);
        }
        var fd = new FormData();
        fd.append('text', plainText);
        fetch(previewUrl, {
          method: 'POST',
          headers: { 'X-CSRFToken': getCookie('csrftoken') },
          body: fd,
          credentials: 'same-origin',
        })
          .then(function (r) { return r.json(); })
          .then(function (j) { previewElement.innerHTML = j.html || ''; })
          .catch(function () { previewElement.innerHTML = '<p style="color:#b91c1c">preview failed</p>'; });
        return 'Загрузка превью…';
      },
    });

    // Drag-n-drop / paste картинок
    if (uploadUrl) {
      var cm = mde.codemirror;
      cm.on('drop', function (cm, e) {
        if (!e.dataTransfer || !e.dataTransfer.files || e.dataTransfer.files.length === 0) return;
        e.preventDefault();
        Array.prototype.forEach.call(e.dataTransfer.files, function (file) {
          if (!file.type.startsWith('image/')) return;
          var placeholder = '![Загрузка ' + file.name + '…]()';
          insertAtCursor(mde, placeholder);
          uploadImage(file, uploadUrl)
            .then(function (j) {
              var doc = cm.getDoc();
              var content = doc.getValue().replace(
                placeholder,
                '![' + (file.name.replace(/\.[^.]+$/, '') || 'image') + '](' + j.url + ')'
              );
              doc.setValue(content);
            })
            .catch(function (err) {
              alert('Ошибка загрузки картинки: ' + err.message);
              var doc = cm.getDoc();
              doc.setValue(doc.getValue().replace(placeholder, ''));
            });
        });
      });

      cm.on('paste', function (cm, e) {
        if (!e.clipboardData || !e.clipboardData.items) return;
        var items = e.clipboardData.items;
        for (var i = 0; i < items.length; i++) {
          if (items[i].kind === 'file' && items[i].type.startsWith('image/')) {
            e.preventDefault();
            var file = items[i].getAsFile();
            var placeholder = '![Загрузка из буфера…]()';
            insertAtCursor(mde, placeholder);
            uploadImage(file, uploadUrl)
              .then(function (j) {
                var doc = cm.getDoc();
                doc.setValue(doc.getValue().replace(placeholder, '![image](' + j.url + ')'));
              })
              .catch(function (err) {
                alert('Ошибка вставки картинки: ' + err.message);
              });
            return;
          }
        }
      });
    }
  }

  function init() {
    var textareas = document.querySelectorAll('textarea.markdown-editor');
    textareas.forEach(initEditor);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
