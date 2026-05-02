/* ============================================================
   Brian & Aisha Wedding — site JS
   ============================================================ */
(function () {
  'use strict';

  /* ----------------- Cookie helpers ----------------- */
  function getCookie(name) {
    var m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? decodeURIComponent(m.pop()) : '';
  }
  function setCookie(name, value, maxAgeSec) {
    document.cookie = name + '=' + encodeURIComponent(value) + '; max-age=' + maxAgeSec + '; path=/; samesite=Lax';
  }

  function clearCookie(name) {
    document.cookie = name + '=; max-age=0; path=/; samesite=Lax';
  }

  /* ----------------- Envelope intro/close toggle ---------------- */
  function setupHomeEnvelope() {
    var envelopeSection = document.getElementById('envelope-section');
    var homeContent     = document.getElementById('home-content');
    var envelopeImg     = document.getElementById('envelope-img');
    var closeBtn        = document.getElementById('envelope-close-btn');

    if (!envelopeSection || !homeContent) return;

    function openEnvelope() {
      envelopeSection.style.transition = 'opacity 0.4s ease';
      envelopeSection.style.opacity = '0';
      setTimeout(function () {
        envelopeSection.style.display = 'none';
        homeContent.style.display = 'block';
        homeContent.style.opacity = '0';
        homeContent.style.transform = 'translateY(60px)';
        homeContent.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
        requestAnimationFrame(function () {
          requestAnimationFrame(function () {
            homeContent.style.opacity = '1';
            homeContent.style.transform = 'translateY(0)';
          });
        });
        document.cookie = 'envelope_opened=1; max-age=86400; path=/';
      }, 400);
    }

    function closeEnvelope() {
      homeContent.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      homeContent.style.opacity = '0';
      homeContent.style.transform = 'translateY(60px)';
      setTimeout(function () {
        homeContent.style.display = 'none';
        homeContent.style.opacity = '0';
        homeContent.style.transform = '';
        homeContent.style.transition = '';
        envelopeSection.style.display = 'flex';
        envelopeSection.style.opacity = '0';
        envelopeSection.style.transition = 'opacity 0.4s ease';
        requestAnimationFrame(function () {
          requestAnimationFrame(function () {
            envelopeSection.style.opacity = '1';
          });
        });
        document.cookie = 'envelope_opened=; max-age=0; path=/';
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }, 400);
    }

    if (getCookie('envelope_opened')) {
      envelopeSection.style.display = 'none';
      homeContent.style.display = 'block';
      homeContent.style.opacity = '1';
      homeContent.style.transform = 'none';
    }

    if (envelopeImg) envelopeImg.addEventListener('click', openEnvelope);
    if (closeBtn)    closeBtn.addEventListener('click', closeEnvelope);
  }

  /* ----------------- Countdown ----------------- */
  function setupCountdown() {
    var root = document.querySelector('.aw-countdown');
    if (!root) return;
    var target = new Date('2026-09-05T17:30:00-05:00');
    var elDays = root.querySelector('[data-d]');
    var elHrs  = root.querySelector('[data-h]');
    var elMin  = root.querySelector('[data-m]');
    var elSec  = root.querySelector('[data-s]');

    function tick() {
      var diff = target - new Date();
      if (diff <= 0) {
        if (elDays) elDays.textContent = '0';
        if (elHrs)  elHrs.textContent  = '0';
        if (elMin)  elMin.textContent  = '0';
        if (elSec)  elSec.textContent  = '0';
        return;
      }
      var days = Math.floor(diff / 86400000);
      var hrs  = Math.floor((diff % 86400000) / 3600000);
      var min  = Math.floor((diff % 3600000) / 60000);
      var sec  = Math.floor((diff % 60000) / 1000);
      if (elDays) elDays.textContent = days;
      if (elHrs)  elHrs.textContent  = hrs;
      if (elMin)  elMin.textContent  = min;
      if (elSec)  elSec.textContent  = sec;
    }
    tick();
    setInterval(tick, 1000);
  }

  /* ----------------- RSVP plugin ----------------- */
  function setupRSVPPlugin() {
    var conf = window.AW_RSVP_CONF;
    if (!conf) return;

    var $  = function (sel, root) { return (root || document).querySelector(sel); };
    var $$ = function (sel, root) {
      return Array.prototype.slice.call((root || document).querySelectorAll(sel));
    };

    var events = (conf.events || []).map(function (e) {
      if (typeof e === 'string') {
        return { id: e.toLowerCase().replace(/\s+/g, '-'), label: e };
      }
      return e;
    });

    // Gate (lookup) elements
    var gate            = $('#aw-rsvp-gate');
    var gateEmail       = $('#aw-lookup-email');
    var gateBtn         = $('#aw-lookup-btn');
    var gateError       = $('#aw-lookup-error');
    var gateSuccess     = $('#aw-lookup-success');
    var gateMax         = $('#aw-gate-max');
    var gateNameToggle  = $('#aw-lookup-name-toggle');
    var gateNameWrap    = $('#aw-lookup-name-wrap');
    var gateNameBtn     = $('#aw-lookup-name-btn');
    var gateFirst       = $('#aw-lookup-first');
    var gateLast        = $('#aw-lookup-last');
    var gateMultiple    = $('#aw-lookup-multiple');

    // Form elements
    var app             = $('#aw-rsvp-app');
    var elEvents        = $('#aw-events');
    var elGuests        = $('#aw-guests');
    var elCount         = $('#aw-count');
    var elCount2        = $('#aw-count-2');
    var elEmail         = $('#aw-email');
    var elPhone         = $('#aw-phone');
    var elNotes         = $('#aw-notes');
    var elPreview       = $('#aw-preview');
    var elSummary       = $('#aw-summary');
    var elSubmit        = $('#aw-submit');
    var elSuccess       = $('#aw-success');
    var elError         = $('#aw-error');
    var elHp            = $('#aw-hp');
    var btnAdd          = $('#aw-add-guest');
    var btnClear        = $('#aw-clear-guests');
    var elMax           = $('#aw-max');
    var elMax2          = $('#aw-max-2');
    var elHouseholdLbl  = $('#aw-household-label');
    var elHeaderMeta    = $('#aw-header-meta');

    if (!gate || !app) return; // not on the RSVP page

    var inviteId = null;
    var maxGuests = conf.maxGuests || 2;

    function showLookupError(msg) {
      if (gateError) {
        gateError.textContent = msg || 'We could not find that invite.';
        gateError.style.display = 'block';
      }
      if (gateSuccess) gateSuccess.style.display = 'none';
    }
    function hideLookupError() {
      if (gateError) gateError.style.display = 'none';
    }

    function getTopSelectedEvents() {
      return $$('#aw-events input[type="checkbox"]:checked')
        .map(function (c) { return c.dataset.event; });
    }

    function updateCount() {
      var count = $$('#aw-guests .aw-guest input.aw-guest-name')
        .filter(function (i) { return i.value.trim(); })
        .length;
      if (elCount)  elCount.textContent  = count;
      if (elCount2) elCount2.textContent = count;
      if (elMax)    elMax.textContent    = maxGuests;
      if (elMax2)   elMax2.textContent   = maxGuests;
    }

    function renderTopEvents(prechecked) {
      if (!elEvents) return;
      var checkedSet = prechecked || events.map(function (e) { return e.label; });
      elEvents.innerHTML = '';
      events.forEach(function (e) {
        var checked = checkedSet.indexOf(e.label) !== -1 ? 'checked' : '';
        var label = document.createElement('label');
        label.className = 'aw-chip';
        label.innerHTML =
          '<input type="checkbox" data-event="' + e.label + '" ' + checked + '> ' + e.label;
        elEvents.appendChild(label);
      });
    }

    function setupTopEventSync() {
      if (!elEvents) return;
      elEvents.addEventListener('change', function (ev) {
        var t = ev.target;
        if (!t || !t.matches || !t.matches('input[type="checkbox"][data-event]')) return;
        var evtName = t.dataset.event;
        $$('#aw-guests input[type="checkbox"][data-event="' + evtName + '"]').forEach(function (c) {
          c.checked = t.checked;
        });
        refreshSummary();
      });
    }

    function escAttr(s) {
      return String(s == null ? '' : s).replace(/"/g, '&quot;');
    }

    function renumberCards() {
      $$('#aw-guests .aw-guest').forEach(function (card, i) {
        var t = card.querySelector('.aw-guest-title');
        if (t) t.textContent = 'Guest ' + (i + 1);
      });
    }

    function addGuest(prefill) {
      if (!elGuests) return;
      var existing = $$('#aw-guests .aw-guest');
      if (existing.length >= maxGuests) return;

      prefill = prefill || {};
      var card = document.createElement('div');
      card.className = 'aw-guest';
      card.dataset.guestId = prefill.id || ('g' + Math.random().toString(36).slice(2, 8));

      var number = existing.length + 1;
      var top = getTopSelectedEvents();
      var guestEvents = prefill.events || top;

      var checksHtml = events.map(function (e) {
        var checked = guestEvents.indexOf(e.label) !== -1 ? 'checked' : '';
        return '<label class="aw-chip"><input type="checkbox" data-event="' + e.label + '" ' + checked + '> ' + e.label + '</label>';
      }).join('');

      card.innerHTML =
        '<button type="button" class="aw-icon-btn aw-guest-delete" aria-label="Remove guest">&times;</button>' +
        '<div class="aw-guest-title">Guest ' + number + '</div>' +
        '<div class="aw-guest-row">' +
          '<input type="text" class="aw-guest-name" placeholder="Full name" value="' + escAttr(prefill.name) + '">' +
          '<select class="aw-guest-type">' +
            '<option value="adult"' + (prefill.type === 'child' ? '' : ' selected') + '>Adult</option>' +
            '<option value="child"' + (prefill.type === 'child' ? ' selected' : '') + '>Child</option>' +
          '</select>' +
        '</div>' +
        '<div class="aw-guest-events">' + checksHtml + '</div>';

      card.querySelector('.aw-guest-delete').addEventListener('click', function () {
        card.remove();
        renumberCards();
        refreshSummary();
      });
      card.addEventListener('input', refreshSummary);
      card.addEventListener('change', refreshSummary);

      elGuests.appendChild(card);
      refreshSummary();
    }

    function buildPayload() {
      var guests = $$('#aw-guests .aw-guest').map(function (card) {
        var nameInput = card.querySelector('input.aw-guest-name');
        var typeSelect = card.querySelector('select.aw-guest-type');
        var checks = $$('input[type="checkbox"][data-event]', card);
        return {
          id: card.dataset.guestId || ('g' + Math.random().toString(36).slice(2, 8)),
          name: ((nameInput && nameInput.value) || '').trim(),
          type: typeSelect ? typeSelect.value : 'adult',
          events: checks.filter(function (c) { return c.checked; })
                        .map(function (c) { return c.dataset.event; })
        };
      }).filter(function (g) { return g.name; });

      return {
        household: conf.household || 'Your household',
        invite_id: inviteId,
        maxGuests: maxGuests,
        events: events,
        topEventSelections: getTopSelectedEvents(),
        guests: guests,
        contact: {
          email: ((elEmail && elEmail.value) || '').trim(),
          phone: ((elPhone && elPhone.value) || '').trim()
        },
        notes: ((elNotes && elNotes.value) || '').trim(),
        notify: conf.notify || '',
        secret: conf.secret || '',
        hp: (elHp && elHp.value) || '',
        submittedAt: new Date().toISOString()
      };
    }

    function buildSummary(p) {
      var lines = [];
      lines.push('Household: ' + p.household);
      lines.push('');
      lines.push('Top events: ' + (p.topEventSelections.join(', ') || '(none)'));
      lines.push('');
      lines.push('Guests:');
      if (!p.guests.length) {
        lines.push('  (none yet)');
      } else {
        p.guests.forEach(function (g) {
          var ev = (g.events || []).join(', ') || '(none)';
          lines.push('  - ' + g.name + ' (' + g.type + ') — ' + ev);
        });
      }
      lines.push('');
      lines.push('Contact:');
      lines.push('  Email: ' + (p.contact.email || '—'));
      lines.push('  Phone: ' + (p.contact.phone || '—'));
      if (p.notes) {
        lines.push('');
        lines.push('Notes: ' + p.notes);
      }
      return lines.join('\n');
    }

    function refreshSummary() {
      var p = buildPayload();
      if (elSummary) elSummary.textContent = buildSummary(p);
      updateCount();
    }

    function prefillFromExisting(rsvp) {
      if (!rsvp) return;
      if (elEmail && rsvp.email) elEmail.value = rsvp.email;
      if (elPhone && rsvp.phone) elPhone.value = rsvp.phone;
      if (elNotes && rsvp.notes) elNotes.value = rsvp.notes;

      if (rsvp.events && rsvp.events.length) {
        renderTopEvents(rsvp.events);
      }

      if (elGuests) elGuests.innerHTML = '';
      (rsvp.guests || []).forEach(function (g) {
        var name = (g.first_name || '') + (g.last_name ? ' ' + g.last_name : '');
        addGuest({ name: name.trim(), type: g.type || 'adult' });
      });
      if (!$$('#aw-guests .aw-guest').length) addGuest({});
    }

    function showFormFromInvite(data) {
      inviteId = data.invite_id || data.id || null;
      maxGuests = data.max_guests || conf.maxGuests || 2;
      if (gate) gate.style.display = 'none';
      if (app) app.style.display = 'block';
      if (elHeaderMeta) elHeaderMeta.classList.remove('aw-hide-meta');
      if (elHouseholdLbl) {
        elHouseholdLbl.textContent = data.full_name || conf.household || 'Your household';
      }
      if (elMax)  elMax.textContent  = maxGuests;
      if (elMax2) elMax2.textContent = maxGuests;
      if (elEmail && data.email && !elEmail.value) elEmail.value = data.email;

      renderTopEvents();

      if (data.rsvp) {
        prefillFromExisting(data.rsvp);
      } else {
        if (elGuests) elGuests.innerHTML = '';
        addGuest({ name: data.full_name || '' });
      }
      refreshSummary();
    }

    function renderMultiple(candidates) {
      if (!gateMultiple) return;
      gateMultiple.innerHTML = '<p class="aw-muted">Multiple matches — pick one:</p>';
      candidates.forEach(function (c) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'aw-btn';
        btn.style.margin = '4px 6px 4px 0';
        btn.textContent = c.full_name + (c.email ? ' (' + c.email + ')' : '');
        btn.addEventListener('click', function () {
          if (c.email) {
            fetch(conf.lookupUrl + '?email=' + encodeURIComponent(c.email))
              .then(function (r) { return r.json(); })
              .then(function (d) {
                if (d.found && !d.multiple) {
                  showFormFromInvite(d);
                } else {
                  showFormFromInvite({
                    invite_id: c.id,
                    full_name: c.full_name,
                    email: c.email,
                    max_guests: c.max_guests
                  });
                }
              })
              .catch(function () {
                showFormFromInvite({
                  invite_id: c.id,
                  full_name: c.full_name,
                  email: c.email,
                  max_guests: c.max_guests
                });
              });
          } else {
            showFormFromInvite({
              invite_id: c.id,
              full_name: c.full_name,
              email: '',
              max_guests: c.max_guests
            });
          }
        });
        gateMultiple.appendChild(btn);
      });
      gateMultiple.style.display = 'block';
    }

    function handleLookupResponse(data) {
      if (!data || !data.found) {
        showLookupError('We could not find that invite.');
        return;
      }
      if (data.multiple) {
        renderMultiple(data.candidates || []);
        return;
      }
      hideLookupError();
      if (gateSuccess) gateSuccess.style.display = 'block';
      if (gateMax) gateMax.textContent = data.max_guests;
      showFormFromInvite(data);
    }

    if (gateBtn) {
      gateBtn.addEventListener('click', function () {
        hideLookupError();
        if (gateMultiple) gateMultiple.style.display = 'none';
        var email = ((gateEmail && gateEmail.value) || '').trim();
        if (!email) { showLookupError('Please enter your email.'); return; }
        fetch(conf.lookupUrl + '?email=' + encodeURIComponent(email))
          .then(function (r) { return r.json(); })
          .then(handleLookupResponse)
          .catch(function () { showLookupError('Something went wrong. Please try again.'); });
      });
    }

    if (gateNameToggle && gateNameWrap) {
      gateNameToggle.addEventListener('click', function () {
        var hidden = gateNameWrap.style.display === 'none' || !gateNameWrap.style.display;
        gateNameWrap.style.display = hidden ? 'block' : 'none';
      });
    }

    if (gateNameBtn) {
      gateNameBtn.addEventListener('click', function () {
        hideLookupError();
        if (gateMultiple) gateMultiple.style.display = 'none';
        var f = ((gateFirst && gateFirst.value) || '').trim();
        var l = ((gateLast && gateLast.value) || '').trim();
        if (!f && !l) { showLookupError('Please enter a first or last name.'); return; }
        var params = [];
        if (f) params.push('first_name=' + encodeURIComponent(f));
        if (l) params.push('last_name=' + encodeURIComponent(l));
        fetch(conf.lookupUrl + '?' + params.join('&'))
          .then(function (r) { return r.json(); })
          .then(handleLookupResponse)
          .catch(function () { showLookupError('Something went wrong. Please try again.'); });
      });
    }

    setupTopEventSync();

    if (btnClear) {
      btnClear.addEventListener('click', function () {
        if (elGuests) elGuests.innerHTML = '';
        refreshSummary();
      });
    }

    if (btnAdd) {
      btnAdd.addEventListener('click', function () { addGuest({}); });
    }

    if (elPreview) {
      elPreview.addEventListener('click', function () {
        refreshSummary();
        if (elSuccess) elSuccess.hidden = true;
        if (elError)   elError.hidden   = true;
      });
    }

    if (elSubmit) {
      elSubmit.addEventListener('click', function () {
        var payload = buildPayload();
        refreshSummary();
        if (!payload.guests.length || !payload.contact.email) {
          if (elError) {
            elError.hidden = false;
            elError.textContent = 'Please add at least one guest and a contact email.';
          }
          if (elSuccess) elSuccess.hidden = true;
          return;
        }

        elSubmit.disabled = true;
        fetch(conf.restUrl, {
          method: 'POST',
          credentials: 'same-origin',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify(payload)
        })
        .then(function (r) {
          return r.json().then(function (body) { return { ok: r.ok, body: body }; });
        })
        .then(function (res) {
          elSubmit.disabled = false;
          if (res.ok && res.body && res.body.ok) {
            if (elSuccess) elSuccess.hidden = false;
            if (elError)   elError.hidden   = true;
          } else {
            if (elError) {
              elError.hidden = false;
              elError.textContent = (res.body && res.body.error) || "There's an issue with your RSVP. Please check required fields.";
            }
            if (elSuccess) elSuccess.hidden = true;
          }
        })
        .catch(function () {
          elSubmit.disabled = false;
          if (elError) {
            elError.hidden = false;
            elError.textContent = 'Network error. Please try again.';
          }
          if (elSuccess) elSuccess.hidden = true;
        });
      });
    }
  }

  /* ----------------- FAQ scroll-spy ----------------- */
  function setupFAQ() {
    var pills = document.querySelectorAll('.aw-pill');
    var sections = document.querySelectorAll('.aw-faq-section');
    if (!pills.length || !sections.length) return;

    // No header/navbar — sticky pills sit flush at the top.
    document.documentElement.style.setProperty('--aw-top-offset', '0px');

    var pillById = {};
    pills.forEach(function (p) {
      var id = p.getAttribute('href');
      if (id && id.charAt(0) === '#') pillById[id.slice(1)] = p;
      p.addEventListener('click', function (e) {
        e.preventDefault();
        var target = document.getElementById(id.slice(1));
        if (!target) return;
        var topOffset = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--aw-top-offset')) || 0;
        var top = target.getBoundingClientRect().top + window.scrollY - topOffset - 20;
        window.scrollTo({ top: top, behavior: 'smooth' });
      });
    });

    function setActive(id) {
      pills.forEach(function (p) { p.classList.remove('is-active'); });
      var p = pillById[id];
      if (p) p.classList.add('is-active');
    }

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) setActive(entry.target.id);
      });
    }, { rootMargin: '-40% 0px -55% 0px', threshold: 0 });
    sections.forEach(function (s) { io.observe(s); });
  }

  /* ----------------- Boot ----------------- */
  document.addEventListener('DOMContentLoaded', function () {
    setupHomeEnvelope();
    setupCountdown();
    setupRSVPPlugin();
    setupFAQ();
  });
})();
