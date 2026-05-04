const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

function toast(message, type = 'success') {
  const node = document.createElement('div');
  node.className = `toast toast-${type}`;
  node.textContent = message;
  Object.assign(node.style, {
    position: 'fixed',
    left: '50%',
    bottom: '28px',
    transform: 'translateX(-50%) translateY(20px)',
    background: type === 'danger' ? '#dc2626' : '#111936',
    color: '#fff',
    padding: '12px 16px',
    borderRadius: '999px',
    boxShadow: '0 16px 50px rgba(0,0,0,.24)',
    zIndex: '100',
    opacity: '0',
    transition: 'all .22s ease',
    maxWidth: 'min(92vw, 520px)',
    textAlign: 'center',
    fontWeight: '800'
  });
  document.body.appendChild(node);
  requestAnimationFrame(() => {
    node.style.opacity = '1';
    node.style.transform = 'translateX(-50%) translateY(0)';
  });
  setTimeout(() => {
    node.style.opacity = '0';
    node.style.transform = 'translateX(-50%) translateY(20px)';
    setTimeout(() => node.remove(), 260);
  }, 2400);
}

async function handleCartForm(form) {
  const submit = form.querySelector('button[type="submit"], button:not([type])');
  const original = submit?.textContent || 'Add to Cart';
  if (submit) {
    submit.disabled = true;
    submit.textContent = 'Adding...';
  }
  try {
    const response = await fetch(form.action, {
      method: 'POST',
      headers: { 'X-CSRF-Token': csrfToken, 'X-Requested-With': 'fetch' },
      body: new FormData(form)
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || 'Unable to add item.');
    document.querySelectorAll('#cart-count').forEach(el => el.textContent = payload.cart_count);
    toast(payload.message || 'Added to cart.');
    const card = form.closest('.product-card, .detail-shell');
    if (card) {
      card.animate([
        { transform: 'scale(1)' },
        { transform: 'scale(1.015)' },
        { transform: 'scale(1)' }
      ], { duration: 260, easing: 'ease-out' });
    }
  } catch (error) {
    toast(error.message, 'danger');
  } finally {
    if (submit) {
      submit.disabled = false;
      submit.textContent = original;
    }
  }
}

document.querySelectorAll('.add-cart-form').forEach(form => {
  form.addEventListener('submit', event => {
    event.preventDefault();
    handleCartForm(form);
  });
});

function applyTilt(card, strength = 10) {
  card.addEventListener('mousemove', event => {
    const rect = card.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const rotateY = ((x / rect.width) - 0.5) * strength;
    const rotateX = ((0.5 - y / rect.height)) * strength;
    card.style.transform = `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
  });
  card.addEventListener('mouseleave', () => {
    card.style.transform = '';
  });
}

document.querySelectorAll('.tilt-card').forEach(card => applyTilt(card, 7));
document.querySelectorAll('[data-tilt-card]').forEach(card => applyTilt(card, 14));

const revealObserver = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible-now');
      revealObserver.unobserve(entry.target);
    }
  });
}, { threshold: 0.08 });

document.querySelectorAll('.product-card').forEach((card, index) => {
  card.style.animationDelay = `${Math.min(index * 22, 360)}ms`;
  revealObserver.observe(card);
});

window.addEventListener('DOMContentLoaded', () => {
  document.body.classList.add('is-ready');
});

document.querySelectorAll('a[href]').forEach(link => {
  const href = link.getAttribute('href') || '';
  const isInternal = href.startsWith('/') || href.startsWith(window.location.origin);
  if (!isInternal || href.startsWith('#') || link.target === '_blank') return;
  link.addEventListener('click', event => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    document.body.classList.add('is-leaving');
  });
});

const product3dObject = document.getElementById('product3dObject');
let product3dRotation = 0;
function setProductRotation(delta) {
  if (!product3dObject) return;
  product3dObject.classList.remove('is-spinning');
  product3dRotation += delta;
  product3dObject.style.transform = `rotateY(${product3dRotation}deg) rotateX(5deg)`;
}
document.querySelector('[data-rotate-left]')?.addEventListener('click', () => setProductRotation(-28));
document.querySelector('[data-rotate-right]')?.addEventListener('click', () => setProductRotation(28));
document.querySelector('[data-spin-toggle]')?.addEventListener('click', () => {
  if (!product3dObject) return;
  product3dObject.style.transform = '';
  product3dObject.classList.toggle('is-spinning');
});


/* Advanced image upload, crop/resize preview, gallery preview, zoom, and 360 viewer */
function fileListFrom(files) {
  const dt = new DataTransfer();
  Array.from(files || []).forEach(file => dt.items.add(file));
  return dt.files;
}

function connectDropZone(zone, input) {
  if (!zone || !input) return;
  ['dragenter', 'dragover'].forEach(type => {
    zone.addEventListener(type, event => {
      event.preventDefault();
      zone.classList.add('drag-over');
    });
  });
  ['dragleave', 'drop'].forEach(type => {
    zone.addEventListener(type, event => {
      event.preventDefault();
      zone.classList.remove('drag-over');
    });
  });
  zone.addEventListener('drop', event => {
    const files = event.dataTransfer?.files;
    if (!files?.length) return;
    input.files = input.multiple ? fileListFrom(files) : fileListFrom([files[0]]);
    input.dispatchEvent(new Event('change', { bubbles: true }));
  });
}

function initPrimaryImageUploader(zone) {
  const input = zone.querySelector('input[type="file"][name="image_file"]');
  const preview = zone.querySelector('[data-image-preview]');
  const zoom = zone.querySelector('[data-crop-zoom]');
  const formId = zone.dataset.formId;
  const hidden = zone.querySelector('[data-cropped-output]') ||
    (formId ? document.querySelector(`input[data-cropped-output][form="${formId}"]`) : null);
  let loadedImage = null;

  connectDropZone(zone, input);

  function renderCrop() {
    if (!loadedImage || !hidden || !preview) return;
    const canvas = document.createElement('canvas');
    canvas.width = 900;
    canvas.height = 900;
    const ctx = canvas.getContext('2d');
    const cropZoom = Math.max(1, parseFloat(zoom?.value || '1'));
    const sourceSize = Math.min(loadedImage.naturalWidth, loadedImage.naturalHeight) / cropZoom;
    const sx = (loadedImage.naturalWidth - sourceSize) / 2;
    const sy = (loadedImage.naturalHeight - sourceSize) / 2;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(loadedImage, sx, sy, sourceSize, sourceSize, 0, 0, canvas.width, canvas.height);
    const dataUrl = canvas.toDataURL('image/png', 0.92);
    hidden.value = dataUrl;
    preview.innerHTML = `<img src="${dataUrl}" alt="Cropped product preview"><span>900×900 crop ready</span>`;
  }

  input?.addEventListener('change', () => {
    const file = input.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        loadedImage = img;
        renderCrop();
        zone.classList.add('has-preview');
      };
      img.onerror = () => {
        if (preview) preview.innerHTML = `<img src="${reader.result}" alt="Product preview"><span>Preview ready</span>`;
        if (hidden) hidden.value = '';
      };
      img.src = reader.result;
    };
    reader.readAsDataURL(file);
  });

  zoom?.addEventListener('input', renderCrop);
}

function initGalleryUploader(zone) {
  const input = zone.querySelector('input[type="file"][name="gallery_images"]');
  const preview = zone.querySelector('[data-gallery-preview]');
  connectDropZone(zone, input);
  input?.addEventListener('change', () => {
    if (!preview) return;
    preview.innerHTML = '';
    Array.from(input.files || []).slice(0, 12).forEach(file => {
      const reader = new FileReader();
      reader.onload = () => {
        const tile = document.createElement('div');
        tile.className = 'gallery-preview-tile';
        tile.innerHTML = `<img src="${reader.result}" alt="${file.name}"><span>${file.name}</span>`;
        preview.appendChild(tile);
      };
      reader.readAsDataURL(file);
    });
  });
}

document.querySelectorAll('[data-image-uploader]').forEach(initPrimaryImageUploader);
document.querySelectorAll('[data-gallery-uploader]').forEach(initGalleryUploader);

function initProductGalleryViewer(viewer) {
  let images = [];
  try {
    images = JSON.parse(viewer.dataset.images || '[]');
  } catch (_error) {
    images = [];
  }
  if (!images.length) return;
  const main = viewer.querySelector('[data-main-gallery-image]');
  const modal = document.getElementById('zoomModal');
  const modalImg = modal?.querySelector('img');
  const thumbs = viewer.querySelectorAll('[data-gallery-index]');
  let index = 0;
  let timer = null;

  function show(nextIndex) {
    index = (nextIndex + images.length) % images.length;
    if (main) {
      main.style.opacity = '0';
      setTimeout(() => {
        main.src = images[index];
        if (modalImg) modalImg.src = images[index];
        main.style.opacity = '1';
      }, 90);
    }
    thumbs.forEach(btn => btn.classList.toggle('active', Number(btn.dataset.galleryIndex) === index));
  }

  viewer.querySelector('[data-gallery-prev]')?.addEventListener('click', () => show(index - 1));
  viewer.querySelector('[data-gallery-next]')?.addEventListener('click', () => show(index + 1));
  thumbs.forEach(btn => btn.addEventListener('click', () => show(Number(btn.dataset.galleryIndex || 0))));

  viewer.querySelector('[data-spin-toggle]')?.addEventListener('click', () => {
    if (timer) {
      clearInterval(timer);
      timer = null;
      toast('360° auto view paused.');
      return;
    }
    timer = setInterval(() => show(index + 1), 850);
    toast('360° auto view started.');
  });

  const zoomFrame = viewer.querySelector('[data-zoom-frame]');
  zoomFrame?.addEventListener('mousemove', event => {
    const rect = zoomFrame.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 100;
    const y = ((event.clientY - rect.top) / rect.height) * 100;
    if (main) {
      main.style.transformOrigin = `${x}% ${y}%`;
      main.style.transform = 'translateZ(64px) scale(1.85)';
    }
  });
  zoomFrame?.addEventListener('mouseleave', () => {
    if (main) {
      main.style.transformOrigin = 'center';
      main.style.transform = 'translateZ(64px) scale(1)';
    }
  });

  viewer.querySelector('[data-open-zoom]')?.addEventListener('click', () => {
    if (!modal || !modalImg) return;
    modalImg.src = images[index];
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
  });

  document.querySelector('[data-close-zoom]')?.addEventListener('click', () => {
    modal?.classList.remove('open');
    modal?.setAttribute('aria-hidden', 'true');
  });
  modal?.addEventListener('click', event => {
    if (event.target === modal) {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
    }
  });
}

document.querySelectorAll('[data-gallery-viewer]').forEach(initProductGalleryViewer);
