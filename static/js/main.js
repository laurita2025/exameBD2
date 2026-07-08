document.addEventListener('DOMContentLoaded', function () {
  const examForm = document.getElementById('examForm');
  const examenForm = document.getElementById('examenForm');
  const antiTrampasInput = document.getElementById('anti_trampas');
  const examElement = examForm || examenForm;
  const examIdInput = examElement ? examElement.querySelector('input[name="examen_id"]') : null;
  const examenId = examIdInput ? examIdInput.value : 'aleatorio';

const warningInfo = document.getElementById('warningInfo');
    function reportEvent(eventType) {
      fetch('/api/control_ventana', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ evento: eventType, examen_id: examenId })
      })
        .then(response => response.json())
        .then(data => {
          if (data.warning_count > 0 && data.warning_count < 3) {
            const text = `Advertencia ${data.warning_count}/3: no abandones el examen.`;
            if (warningInfo) {
              warningInfo.textContent = text;
              warningInfo.classList.remove('d-none');
            } else {
              alert(text);
            }
          }
          if (data.blocked) {
            const text = 'Has sido bloqueado por salir del examen demasiadas veces. No podrás continuar.';
            if (warningInfo) {
              warningInfo.textContent = text;
              warningInfo.classList.remove('d-none');
            } else {
              alert(text);
            }
          window.location.href = '/dashboard';
        }
      });
    if (antiTrampasInput) {
      antiTrampasInput.value = parseInt(antiTrampasInput.value || '0') + 1;
    }
  }

  const isExamPage = Boolean(examForm || examenForm);

  if (isExamPage && document.visibilityState === 'hidden') {
    reportEvent('ocultar_pantalla');
  }

  if (isExamPage) {
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'hidden') {
        reportEvent('ocultar_pantalla');
        alert('No abandones la pantalla durante el examen.');
      }
    });

    window.addEventListener('blur', function () {
      reportEvent('perdio_foco');
    });

    window.addEventListener('focus', function () {
      reportEvent('gano_foco');
    });

    window.addEventListener('beforeunload', function () {
      if (navigator.sendBeacon) {
        const data = JSON.stringify({ evento: 'salida', examen_id: examenId });
        const blob = new Blob([data], { type: 'application/json' });
        navigator.sendBeacon('/api/control_ventana', blob);
      }
    });
  }

  const timerLabel = document.getElementById('timer');
  const tiempoInicioInput = document.getElementById('tiempo_inicio');
  const tiempoFinInput = document.getElementById('tiempo_fin');
  if (timerLabel && (examenForm || examForm)) {
    const tiempoParts = timerLabel.textContent.trim().split(':');
    let minutos = parseInt(tiempoParts[0], 10);
    let segundos = parseInt(tiempoParts[1], 10);
    const now = new Date();
    if (tiempoInicioInput) {
      tiempoInicioInput.value = now.toISOString();
    }
    const interval = setInterval(function () {
      if (segundos === 0) {
        if (minutos === 0) {
          clearInterval(interval);
          alert('Se terminó el tiempo. El examen se enviará automáticamente.');
          if (tiempoFinInput) {
            tiempoFinInput.value = new Date().toISOString();
          }
          if (examenForm) {
            examenForm.submit();
          } else if (examForm) {
            examForm.submit();
          }
          return;
        }
        minutos -= 1;
        segundos = 59;
      } else {
        segundos -= 1;
      }
      timerLabel.textContent = `${String(minutos).padStart(2, '0')}:${String(segundos).padStart(2, '0')}`;
    }, 1000);
  }

  if (examenForm) {
    examenForm.addEventListener('submit', function () {
      if (tiempoFinInput) {
        tiempoFinInput.value = new Date().toISOString();
      }
    });
  }

  if (examForm) {
    const now = new Date();
    if (tiempoInicioInput) {
      tiempoInicioInput.value = now.toISOString();
    }
    examForm.addEventListener('submit', function () {
      if (tiempoFinInput) {
        tiempoFinInput.value = new Date().toISOString();
      }
    });
  }
});
