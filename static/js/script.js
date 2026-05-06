(function () {
    function safeNumber(value, fallback = 0) {
        const parsed = Number(value);
        return Number.isFinite(parsed) ? parsed : fallback;
    }

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i += 1) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === `${name}=`) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function escapeHtmlAttr(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }

    function loadExternalScript(src) {
        if (!src) {
            return Promise.resolve();
        }
        const existing = document.querySelector(`script[src="${src}"]`);
        if (existing) {
            if (existing.dataset.loaded === '1') {
                return Promise.resolve();
            }
            return new Promise((resolve, reject) => {
                existing.addEventListener('load', () => resolve(), { once: true });
                existing.addEventListener('error', reject, { once: true });
            });
        }
        return new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = src;
            script.async = true;
            script.onload = () => {
                script.dataset.loaded = '1';
                resolve();
            };
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    window.toggleDescription = function toggleDescription(sheetId) {
        const prefix = sheetId ? `${sheetId}-` : '';
        const desc = document.getElementById(`${prefix}description`) || document.getElementById('description');
        if (!desc) {
            return;
        }
        if (desc.style.display === 'none' || desc.style.display === '') {
            desc.style.display = 'block';
            desc.style.animation = 'slideDown 0.3s ease';
        } else {
            desc.style.display = 'none';
        }
    };

    window.toggleSection = function toggleSection(section, sheetId) {
        const prefix = sheetId ? `${sheetId}-` : '';
        const content = document.getElementById(`${prefix}${section}-content`) || document.getElementById(`${section}-content`);
        const icon = document.getElementById(`${prefix}${section}-icon`) || document.getElementById(`${section}-icon`);
        if (!content || !icon) {
            return;
        }
        if (content.classList.contains('show')) {
            content.classList.remove('show');
            icon.classList.remove('fa-chevron-up');
            icon.classList.add('fa-chevron-down');
        } else {
            content.classList.add('show');
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-up');
        }
    };

    window.showStatModal = function showStatModal(name, value, description) {
        const modal = document.getElementById('statModal');
        if (!modal || !window.bootstrap?.Modal) {
            return;
        }
        const numericValue = safeNumber(value);
        document.getElementById('statModalTitle').textContent = name;
        document.getElementById('statValue').textContent = numericValue;
        document.getElementById('statRegular').textContent = numericValue;
        document.getElementById('statHard').textContent = Math.floor(numericValue / 2);
        document.getElementById('statExtreme').textContent = Math.floor(numericValue / 5);
        document.getElementById('statDescription').textContent = description || '';
        bootstrap.Modal.getOrCreateInstance(modal).show();
    };

    window.showSkillModal = function showSkillModal(name, value, description) {
        const modal = document.getElementById('skillModal');
        if (!modal || !window.bootstrap?.Modal) {
            return;
        }
        const numericValue = safeNumber(value);
        document.getElementById('skillModalTitle').textContent = name;
        document.getElementById('skillValue').textContent = `${numericValue}%`;
        document.getElementById('skillRegular').textContent = numericValue;
        document.getElementById('skillHard').textContent = Math.floor(numericValue / 2);
        document.getElementById('skillExtreme').textContent = Math.floor(numericValue / 5);
        document.getElementById('skillDescription').textContent = description || '';
        bootstrap.Modal.getOrCreateInstance(modal).show();
    };

    window.showSpellModal = function showSpellModal(name, manaCost, description) {
        const modal = document.getElementById('spellModal');
        if (!modal || !window.bootstrap?.Modal) {
            return;
        }
        document.getElementById('spellModalTitle').textContent = name || 'Spell';
        document.getElementById('spellManaCost').textContent = String(safeNumber(manaCost, 0));
        document.getElementById('spellDescription').textContent = description || '';
        bootstrap.Modal.getOrCreateInstance(modal).show();
    };

    window.initSpellBadgePopups = function initSpellBadgePopups() {
        if (document.body.dataset.spellBadgeHandlersBound === '1') {
            return;
        }
        const openSpellModal = (badge) => {
            if (!badge) {
                return;
            }
            window.showSpellModal(
                badge.dataset.spellName || '',
                badge.dataset.spellManaCost || '0',
                badge.dataset.spellDescription || ''
            );
        };

        document.addEventListener('click', (event) => {
            const badge = event.target.closest('.spell-badge');
            if (!badge) {
                return;
            }
            openSpellModal(badge);
        });

        document.addEventListener('keydown', (event) => {
            const target = event.target;
            if (!target || !target.classList?.contains('spell-badge')) {
                return;
            }
            if (event.key !== 'Enter' && event.key !== ' ') {
                return;
            }
            event.preventDefault();
            openSpellModal(target);
        });

        document.body.dataset.spellBadgeHandlersBound = '1';
    };

    window.showAddSkillModal = function showAddSkillModal() {
        const modalElement = document.getElementById('addSkillModal');
        if (!modalElement || !window.bootstrap?.Modal) {
            return;
        }
        bootstrap.Modal.getOrCreateInstance(modalElement).show();
    };

    window.toggleDefaultSkills = function toggleDefaultSkills(sheetId) {
        const prefix = sheetId ? `${sheetId}-` : '';
        const defaultSkills = document.getElementById(`${prefix}default-skills`) || document.getElementById('default-skills');
        const button = document.getElementById(`${prefix}default-skills-btn`) || document.getElementById('default-skills-btn');
        if (!defaultSkills || !button) {
            return;
        }
        if (defaultSkills.classList.contains('show')) {
            defaultSkills.classList.remove('show');
            button.textContent = button.dataset.defaultText || button.textContent;
        } else {
            defaultSkills.classList.add('show');
            if (!button.dataset.defaultText) {
                button.dataset.defaultText = button.textContent;
            }
            button.textContent = button.dataset.hideText || 'Hide default skills';
        }
    };

    window.addCustomSkill = function addCustomSkill() {
        const name = (document.getElementById('skillName')?.value || '').trim();
        const value = document.getElementById('skillValueInput')?.value;
        if (!name || !value) {
            return;
        }
        const modal = document.getElementById('addSkillModal');
        if (modal && window.bootstrap?.Modal) {
            bootstrap.Modal.getOrCreateInstance(modal).hide();
        }
    };

    window.initEffectBadgePopovers = function initEffectBadgePopovers(scope) {
        if (!window.bootstrap?.Popover) {
            return;
        }
        const root = scope || document;
        root.querySelectorAll('.effect-badge[data-effect-description]').forEach((badge) => {
            const description = (badge.dataset.effectDescription || '').trim();
            if (badge._effectPopover) {
                badge._effectPopover.dispose();
                badge._effectPopover = null;
            }
            if (!description) {
                badge.removeAttribute('data-bs-toggle');
                return;
            }
            badge.setAttribute('data-bs-toggle', 'popover');
            badge.setAttribute('data-bs-trigger', 'focus');
            badge.setAttribute('data-bs-placement', 'top');
            badge._effectPopover = new bootstrap.Popover(badge, {
                container: 'body',
                customClass: 'effect-description-popover',
                html: false,
                content: description,
            });
        });
    };

    function initStatusAdjustControls() {
        const resources = ['hp', 'mp', 'sanity', 'luck'];
        const hiddenInputs = {
            hp: document.getElementById('adjust_hp'),
            mp: document.getElementById('adjust_mp'),
            sanity: document.getElementById('adjust_sanity'),
            luck: document.getElementById('adjust_luck'),
        };
        const hasControls = resources.some((key) => hiddenInputs[key]);
        if (!hasControls) {
            return;
        }

        function updateDisplay(resourceKey, currentValue, maxValue) {
            const fill = document.querySelector(`[data-resource-fill="${resourceKey}"]`);
            const text = document.querySelector(`[data-resource-text="${resourceKey}"]`);
            if (fill) {
                fill.style.width = `${(currentValue / Math.max(maxValue, 1)) * 100}%`;
            }
            if (text) {
                text.textContent = `${currentValue}/${maxValue}`;
            }
        }

        function setResourceFromPosition(barElement, clientX) {
            const resource = barElement.dataset.adjustTarget;
            const input = hiddenInputs[resource];
            const container = barElement.closest('.stat-bar-container');
            if (!resource || !input || !container) {
                return;
            }
            const baseCurrent = Number(container.dataset.current || 0);
            const maxValue = Number(container.dataset.max || 0);
            const rect = barElement.getBoundingClientRect();
            if (rect.width <= 0) {
                return;
            }
            const ratio = clamp((clientX - rect.left) / rect.width, 0, 1);
            const targetCurrent = Math.round(ratio * maxValue);
            const nextAdjustment = clamp(targetCurrent - baseCurrent, -99, 99);
            const nextCurrent = clamp(baseCurrent + nextAdjustment, 0, maxValue);
            input.value = String(nextAdjustment);
            updateDisplay(resource, nextCurrent, maxValue);
        }

        let dragBar = null;
        document.querySelectorAll('.stat-bar-adjustable').forEach((bar) => {
            bar.addEventListener('mousedown', (event) => {
                dragBar = bar;
                setResourceFromPosition(bar, event.clientX);
            });
            bar.addEventListener('click', (event) => {
                setResourceFromPosition(bar, event.clientX);
            });
            bar.addEventListener('touchstart', (event) => {
                const touch = event.touches && event.touches[0];
                if (!touch) {
                    return;
                }
                dragBar = bar;
                setResourceFromPosition(bar, touch.clientX);
            }, { passive: true });
        });

        document.addEventListener('mousemove', (event) => {
            if (!dragBar) {
                return;
            }
            setResourceFromPosition(dragBar, event.clientX);
        });

        document.addEventListener('touchmove', (event) => {
            if (!dragBar) {
                return;
            }
            const touch = event.touches && event.touches[0];
            if (!touch) {
                return;
            }
            setResourceFromPosition(dragBar, touch.clientX);
        }, { passive: true });

        function stopDragging() {
            dragBar = null;
        }

        document.addEventListener('mouseup', stopDragging);
        document.addEventListener('touchend', stopDragging);
    }

    function initCharacterEditPage() {
        const config = document.getElementById('character-edit-config');
        if (!config) {
            return;
        }

        const maxLimits = {
            hp_current: safeNumber(config.dataset.hpMax),
            sanity_current: safeNumber(config.dataset.sanityMax),
            mp_current: safeNumber(config.dataset.mpMax),
            luck: 100,
        };

        window.showToast = function showToast() {
            const toastEl = document.getElementById('updateToast');
            if (!toastEl || !window.bootstrap?.Toast) {
                return;
            }
            const toast = new bootstrap.Toast(toastEl);
            toast.show();
        };

        window.updateStat = function updateStat(statName, value) {
            fetch('', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({
                    stat: statName,
                    value: typeof value === 'string' && value !== '' && !Number.isNaN(Number(value)) ? Number(value) : value,
                }),
            })
                .then((response) => response.json())
                .then((data) => {
                    if (data.success) {
                        window.showToast();
                    } else {
                        window.alert('Error updating character. Please try again.');
                    }
                })
                .catch(() => {
                    window.alert('Error updating character. Please try again.');
                });
        };

        window.adjustStat = function adjustStat(statName, change) {
            const input = document.getElementById(statName);
            const display = document.getElementById(`${statName}_display`);
            if (!input || !display) {
                return;
            }
            let newValue = parseInt(input.value, 10) + change;
            if (newValue < 0) {
                newValue = 0;
            }
            if (maxLimits[statName] && newValue > maxLimits[statName]) {
                newValue = maxLimits[statName];
            }
            input.value = String(newValue);
            display.textContent = String(newValue);
            window.updateStat(statName, newValue);
        };

        window.updateSkill = function updateSkill() {
            window.showToast();
        };

        window.updateNotes = function updateNotes(noteType, value) {
            window.updateStat(noteType, value);
        };

        const confirmAddSkillBtn = document.getElementById('confirm-add-skill-btn');
        if (confirmAddSkillBtn && confirmAddSkillBtn.dataset.bound !== '1') {
            confirmAddSkillBtn.dataset.bound = '1';
            confirmAddSkillBtn.addEventListener('click', () => {
                const skillName = document.getElementById('add-skill-name')?.value.trim() || '';
                if (!skillName) {
                    window.alert('Please enter a skill name');
                    return;
                }
                fetch('', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken'),
                    },
                    body: JSON.stringify({
                        action: 'add_skill',
                        skill_name: skillName,
                        skill_value: 1,
                    }),
                })
                    .then((response) => response.json())
                    .then((data) => {
                        if (!data.success) {
                            window.alert(`Error adding skill: ${data.error || 'Unknown error'}`);
                            return;
                        }
                        const skillsContainer = document.querySelector('.stat-group .row.g-3');
                        if (skillsContainer) {
                            const newRow = document.createElement('div');
                            newRow.className = 'col-md-6 col-lg-4';
                            newRow.id = `skill_${data.skill_id}`;
                            newRow.innerHTML = `
                                <div class="d-flex justify-content-between align-items-center">
                                    <label class="form-label mb-0">${escapeHtml(skillName)} <span class="badge bg-info text-dark">Custom</span></label>
                                    <div class="d-flex align-items-center gap-1">
                                        <input type="number" class="form-control stat-input" style="width: 60px;"
                                               value="1" min="0" max="100"
                                               onchange="updateSkill(${data.skill_id}, this.value)">
                                        <span class="text-muted">%</span>
                                    </div>
                                </div>
                            `;
                            skillsContainer.appendChild(newRow);
                        }
                        const input = document.getElementById('add-skill-name');
                        if (input) {
                            input.value = '';
                        }
                        const modalEl = document.getElementById('addSkillModal');
                        if (modalEl && window.bootstrap?.Modal) {
                            bootstrap.Modal.getInstance(modalEl)?.hide();
                        }
                        window.showToast();
                    })
                    .catch(() => {
                        window.alert('Error adding skill. Please try again.');
                    });
            });
        }
    }

    function initScenarioDetailPage() {
        const root = document.getElementById('player-scenario-root');
        if (!root) {
            return;
        }

        const I18N = {
            custom: root.dataset.i18nCustom || 'Custom',
            dodge: root.dataset.i18nDodge || 'Dodge',
            dodgeDesc: root.dataset.i18nDodgeDesc || '',
            noImprovedSkills: root.dataset.i18nNoImprovedSkills || 'No improved skills yet.',
            hideDefaultSkills: root.dataset.i18nHideDefaultSkills || 'Hide default skills',
            showMore: (n) => `${root.dataset.i18nShowMore || 'Show more'} (${n} ${root.dataset.i18nDefaultSkills || 'default skills'})`,
            addCustomSkill: root.dataset.i18nAddCustomSkill || 'Add Custom Skill',
            prepared: root.dataset.i18nPrepared || 'Prepared',
            weapons: root.dataset.i18nWeapons || 'Weapons',
            madnessThreshold: root.dataset.i18nMadnessThreshold || 'Madness threshold',
            noPublicNotes: root.dataset.i18nNoPublicNotes || 'No public notes yet.',
        };

        const dayEl = document.getElementById('session-day');
        const timeEl = document.getElementById('session-time');
        const notesEl = document.getElementById('public-notes');
        const sheetRoot = document.getElementById('player-sheet-root');
        const snapshotUrl = root.dataset.snapshotUrl || '';
        const getMessagesUrl = root.dataset.getMessagesUrl || '';
        const markMessagesReadUrl = root.dataset.markMessagesReadUrl || '';
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
        const messageBadge = document.getElementById('player-message-badge');
        const messagesModalEl = document.getElementById('playerMessagesModal');
        const messagesListEl = document.getElementById('player-messages-list');
        const messagesStatusEl = document.getElementById('player-messages-status');
        const sectionSignatures = { skills: null, combat: null, items: null, spells: null };
        let unreadBaselineReady = true;
        let lastUnreadPrivateMessageId = safeNumber(root.dataset.unreadPrivateMessageId, 0);

        function toSignature(value) {
            return JSON.stringify(value ?? null);
        }

        function setUnreadMessages(count) {
            if (!messageBadge) return;
            if (count > 0) {
                messageBadge.textContent = String(count);
                messageBadge.style.display = 'inline-block';
            } else {
                messageBadge.style.display = 'none';
            }
        }

        function notifyOnNewMessage(unreadCount, latestUnreadPrivateMessageId) {
            const hasNewPrivateMessage = latestUnreadPrivateMessageId > lastUnreadPrivateMessageId;
            if (!unreadBaselineReady) {
                unreadBaselineReady = true;
                lastUnreadPrivateMessageId = latestUnreadPrivateMessageId;
                setUnreadMessages(unreadCount);
                return;
            }
            if (hasNewPrivateMessage) {
                if (messagesModalEl && !messagesModalEl.classList.contains('show') && window.bootstrap?.Modal) {
                    bootstrap.Modal.getOrCreateInstance(messagesModalEl).show();
                }
                if (typeof navigator.vibrate === 'function') {
                    navigator.vibrate([500, 200, 300, 100, 100, 50, 50, 50, 50, 50]);
                }
            }
            lastUnreadPrivateMessageId = latestUnreadPrivateMessageId;
            setUnreadMessages(unreadCount);
        }

        function renderPlayerMessages(messages) {
            if (!messagesListEl) return;
            if (!messages || !messages.length) {
                messagesListEl.innerHTML = '<div class="text-center text-muted py-4"><i class="fas fa-comment-slash mb-2"></i><div>No messages yet</div></div>';
                return;
            }
            messagesListEl.innerHTML = messages.map((msg) => `
                <div class="message-item p-2 mb-2 ${msg.is_unread ? 'unread' : ''}">
                    <div class="message-meta d-flex justify-content-between align-items-center mb-1">
                        <span><strong>${escapeHtml(msg.sender)}</strong>${msg.type === 'PRIVATE' ? ' · Private' : ' · All players'}</span>
                        <span>${new Date(msg.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                    <div class="message-content">${escapeHtml(msg.content)}</div>
                </div>
            `).join('');
        }

        async function loadPlayerMessages(markRead = false) {
            if (!messagesListEl || !getMessagesUrl) return;
            try {
                if (messagesStatusEl) messagesStatusEl.textContent = 'Loading...';
                const res = await fetch(getMessagesUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                const data = await res.json();
                if (!data.ok) return;
                renderPlayerMessages(data.messages || []);
                setUnreadMessages(data.unread_count || 0);
                if (messagesStatusEl) messagesStatusEl.textContent = data.messages?.length ? '' : 'No unread interruptions from the Keeper.';
                if (markRead && (data.unread_count || 0) > 0) {
                    const body = new FormData();
                    if (csrfToken) body.append('csrfmiddlewaretoken', csrfToken);
                    await fetch(markMessagesReadUrl, {
                        method: 'POST',
                        headers: { 'X-Requested-With': 'XMLHttpRequest' },
                        body,
                    });
                    setUnreadMessages(0);
                    renderPlayerMessages((data.messages || []).map((msg) => ({ ...msg, is_unread: false })));
                }
            } catch {
                if (messagesStatusEl) messagesStatusEl.textContent = 'Failed to load messages.';
            }
        }

        function makeSkillItem(skill, extraClass = '') {
            const item = document.createElement('div');
            item.className = `skill-item${extraClass ? ` ${extraClass}` : ''}`;
            const name = document.createElement('span');
            name.className = 'skill-name';
            name.textContent = skill.name || '';
            if (skill.is_custom) {
                const badge = document.createElement('span');
                badge.className = 'badge bg-info text-dark ms-1';
                badge.style.fontSize = '0.7rem';
                badge.textContent = I18N.custom;
                name.appendChild(badge);
            }
            const value = document.createElement('span');
            value.className = 'skill-value';
            value.textContent = `${safeNumber(skill.value)}%`;
            item.appendChild(name);
            item.appendChild(value);
            item.addEventListener('click', () => {
                if (typeof window.showSkillModal === 'function') {
                    window.showSkillModal(skill.name || '', safeNumber(skill.value), skill.description || '');
                }
            });
            return item;
        }

        function renderSkillsSection(payload) {
            const skillsContent = document.getElementById('player-sheet-main-skills-content');
            if (!skillsContent) return;
            const skills = Array.isArray(payload.skills) ? payload.skills : [];
            const defaultSkills = Array.isArray(payload.default_skills) ? payload.default_skills : [];
            const canAddCustomSkill = Boolean(payload.can_add_custom_skill);
            const signature = toSignature({ skills, defaultSkills, canAddCustomSkill });
            if (sectionSignatures.skills === signature) return;
            const wasDefaultSkillsOpen = document.getElementById('player-sheet-main-default-skills')?.classList.contains('show');
            const fragment = document.createDocumentFragment();
            const skillsGrid = document.createElement('div');
            skillsGrid.className = 'skills-grid';
            skillsGrid.dataset.sheetSkillsGrid = '';
            if (skills.length) {
                skills.forEach((skill) => skillsGrid.appendChild(makeSkillItem(skill)));
            } else {
                const empty = document.createElement('div');
                empty.className = 'skill-item';
                const emptyName = document.createElement('span');
                emptyName.className = 'skill-name';
                emptyName.textContent = I18N.noImprovedSkills;
                empty.appendChild(emptyName);
                skillsGrid.appendChild(empty);
            }
            fragment.appendChild(skillsGrid);
            if (defaultSkills.length) {
                const toggleBtn = document.createElement('button');
                toggleBtn.className = 'toggle-default-btn';
                toggleBtn.type = 'button';
                toggleBtn.id = 'player-sheet-main-default-skills-btn';
                const defaultSkillsWrap = document.createElement('div');
                defaultSkillsWrap.className = 'default-skills';
                defaultSkillsWrap.id = 'player-sheet-main-default-skills';
                const defaultGrid = document.createElement('div');
                defaultGrid.className = 'skills-grid';
                defaultSkills.forEach((skill) => defaultGrid.appendChild(makeSkillItem(skill)));
                defaultSkillsWrap.appendChild(defaultGrid);
                toggleBtn.addEventListener('click', () => {
                    defaultSkillsWrap.classList.toggle('show');
                    toggleBtn.textContent = defaultSkillsWrap.classList.contains('show')
                        ? I18N.hideDefaultSkills
                        : I18N.showMore(defaultSkills.length);
                });
                toggleBtn.textContent = wasDefaultSkillsOpen ? I18N.hideDefaultSkills : I18N.showMore(defaultSkills.length);
                if (wasDefaultSkillsOpen) defaultSkillsWrap.classList.add('show');
                fragment.appendChild(toggleBtn);
                fragment.appendChild(defaultSkillsWrap);
            }
            if (canAddCustomSkill) {
                const addSkillBtn = document.createElement('div');
                addSkillBtn.className = 'add-skill-btn';
                addSkillBtn.innerHTML = `<i class="fas fa-plus"></i> ${I18N.addCustomSkill}`;
                addSkillBtn.addEventListener('click', () => {
                    if (typeof window.showAddSkillModal === 'function') {
                        window.showAddSkillModal();
                    }
                });
                fragment.appendChild(addSkillBtn);
            }
            skillsContent.replaceChildren(fragment);
            sectionSignatures.skills = signature;
        }

        function renderCombatSection(payload) {
            const combatContent = document.getElementById('player-sheet-main-combat-content');
            if (!combatContent) return;
            const combatSkills = Array.isArray(payload.combat_skills) ? payload.combat_skills : [];
            const weapons = Array.isArray(payload.weapons) ? payload.weapons : [];
            const dodgeValue = safeNumber(payload.dodge_value);
            const signature = toSignature({ combatSkills, weapons, dodgeValue });
            if (sectionSignatures.combat === signature) return;
            const fragment = document.createDocumentFragment();
            const combatGrid = document.createElement('div');
            combatGrid.className = 'skills-grid';
            combatGrid.dataset.sheetCombatGrid = '';
            combatGrid.appendChild(makeSkillItem({ name: I18N.dodge, value: dodgeValue, description: I18N.dodgeDesc }, 'combat'));
            combatSkills.forEach((skill) => combatGrid.appendChild(makeSkillItem(skill, 'combat')));
            fragment.appendChild(combatGrid);
            if (weapons.length) {
                const weaponsHeader = document.createElement('div');
                weaponsHeader.className = 'compact-header';
                weaponsHeader.innerHTML = `<i class="fas fa-crosshairs"></i> ${I18N.weapons}`;
                fragment.appendChild(weaponsHeader);
                const weaponsWrap = document.createElement('div');
                weaponsWrap.dataset.sheetWeapons = '';
                weapons.forEach((weapon) => {
                    const row = document.createElement('div');
                    row.className = 'weapon-item';
                    const strong = document.createElement('strong');
                    strong.textContent = weapon.name || '';
                    row.appendChild(strong);
                    row.appendChild(document.createTextNode(` ${weapon.damage || ''}`));
                    if (weapon.is_prepared) {
                        const prepared = document.createElement('span');
                        prepared.className = 'text-success';
                        prepared.textContent = ` [${I18N.prepared}]`;
                        row.appendChild(prepared);
                    }
                    weaponsWrap.appendChild(row);
                });
                fragment.appendChild(weaponsWrap);
            }
            combatContent.replaceChildren(fragment);
            sectionSignatures.combat = signature;
        }

        function renderItemsSection(payload) {
            const itemsContent = document.getElementById('player-sheet-main-items-content');
            if (!itemsContent) return;
            const items = Array.isArray(payload.items) ? payload.items : [];
            const cash = safeNumber(payload.character?.cash, 0);
            const signature = JSON.stringify({ cash, items });
            if (sectionSignatures.items === signature) return;
            const wrap = document.createElement('div');
            wrap.className = 'compact-section';
            const grid = document.createElement('div');
            grid.className = 'items-grid';
            grid.dataset.sheetItems = '';
            const cashBadge = document.createElement('span');
            cashBadge.className = 'item-badge cash-badge';
            cashBadge.textContent = `Cash $${cash}`;
            grid.appendChild(cashBadge);
            if (items.length) {
                items.forEach((item) => {
                    const badge = document.createElement('span');
                    badge.className = 'item-badge';
                    badge.textContent = `${item.name || ''} x${safeNumber(item.quantity, 0)}`;
                    grid.appendChild(badge);
                });
            } else {
                const empty = document.createElement('span');
                empty.className = 'item-badge';
                empty.textContent = 'No items';
                grid.appendChild(empty);
            }
            wrap.appendChild(grid);
            itemsContent.replaceChildren(wrap);
            sectionSignatures.items = signature;
        }

        function renderSpellsSection(payload) {
            const spellsSection = document.getElementById('player-sheet-main-spells-section');
            const spellsContent = document.getElementById('player-sheet-main-spells-content') || spellsSection;
            if (!spellsSection || !spellsContent) return;
            const spells = Array.isArray(payload.spells) ? payload.spells : [];
            const signature = JSON.stringify(spells);
            if (sectionSignatures.spells === signature) return;
            if (!spells.length) {
                spellsSection.style.display = 'none';
                spellsContent.replaceChildren();
                sectionSignatures.spells = signature;
                return;
            }
            const list = document.createElement('div');
            list.dataset.sheetSpells = '';
            spells.forEach((spell) => {
                const badge = document.createElement('span');
                badge.className = `badge ${spell.badge_color || 'bg-info'} me-1 mb-1 spell-badge`;
                badge.setAttribute('role', 'button');
                badge.setAttribute('tabindex', '0');
                badge.dataset.spellName = spell.name || '';
                badge.dataset.spellManaCost = String(safeNumber(spell.mana_cost, 0));
                badge.dataset.spellDescription = spell.description || '';
                badge.textContent = spell.name || '';
                list.appendChild(badge);
            });
            spellsSection.style.display = '';
            spellsContent.replaceChildren(list);
            sectionSignatures.spells = signature;
        }

        function updateResource(rootEl, key, current, max) {
            const fill = rootEl.querySelector(`[data-resource-fill="${key}"]`);
            const text = rootEl.querySelector(`[data-resource-text="${key}"]`);
            if (fill) fill.style.width = `${(current / Math.max(max, 1)) * 100}%`;
            if (text) text.textContent = `${current}/${max}`;
        }

        function patchSheet(rootEl, payload) {
            if (!rootEl || !payload) return;
            const activeElement = document.activeElement;
            if (activeElement && rootEl.contains(activeElement)) return;
            const summaryName = document.querySelector('[data-player-sheet-name]');
            if (summaryName) summaryName.textContent = payload.summary?.name || '';
            const summaryOccupation = document.querySelector('[data-player-sheet-occupation]');
            if (summaryOccupation) {
                summaryOccupation.textContent = payload.summary?.occupation ? `• ${payload.summary.occupation}` : '';
            }
            const sheetName = rootEl.querySelector('[data-sheet-name]');
            if (sheetName) sheetName.textContent = payload.character?.name || '';
            const description = rootEl.querySelector('[data-sheet-description]');
            if (description) description.textContent = payload.character?.description || '';
            if (payload.resources) {
                Object.entries(payload.resources).forEach(([key, value]) => updateResource(rootEl, key, value.current, value.max));
            }
            if (payload.stats) {
                Object.entries(payload.stats).forEach(([key, value]) => {
                    const statValue = rootEl.querySelector(`[data-stat-value="${key}"]`);
                    if (statValue) statValue.textContent = String(value ?? '');
                });
                const power = payload.stats.power;
                const sanityMax = payload.resources?.sanity?.max;
                if (power != null && sanityMax) {
                    const threshold = rootEl.querySelector('.san-madness-threshold');
                    if (threshold) {
                        const pct = (power * 0.2) / Math.max(sanityMax, 1) * 100;
                        threshold.style.left = `${pct}%`;
                        threshold.title = `${I18N.madnessThreshold}: ${Math.round(power * 0.2)}`;
                    }
                }
            }
            renderSkillsSection(payload);
            renderCombatSection(payload);
            renderSpellsSection(payload);
            renderItemsSection(payload);
            if (payload.status_effects !== undefined) {
                const charSheet = rootEl.querySelector('.character-sheet[data-character-id]');
                const characterId = charSheet?.dataset.characterId;
                const badgesContainer = characterId ? document.getElementById(`effects-badges-${characterId}`) : null;
                if (badgesContainer) {
                    badgesContainer.innerHTML = (payload.status_effects || []).map((eff) =>
                        `<span class="badge ${escapeHtml(eff.badge_color)} effect-badge" data-effect-description="${escapeHtmlAttr(eff.description || '')}" role="button" tabindex="0">${escapeHtml(eff.name)}</span>`
                    ).join('');
                }
            }
        }

        let snapshotPending = false;
        async function refreshSnapshot() {
            if (snapshotPending || !snapshotUrl) return;
            snapshotPending = true;
            try {
                const res = await fetch(snapshotUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                const data = await res.json();
                if (!data.ok) return;
                if (dayEl) dayEl.textContent = data.day;
                if (timeEl) timeEl.textContent = data.time;
                if (notesEl) notesEl.textContent = data.public_notes || I18N.noPublicNotes;
                notifyOnNewMessage(safeNumber(data.unread_messages, 0), safeNumber(data.latest_unread_private_message_id, 0));
                if (sheetRoot && data.has_alive_character && data.sheet) {
                    patchSheet(sheetRoot, data.sheet);
                } else if ((sheetRoot && !data.has_alive_character) || (!sheetRoot && data.has_alive_character)) {
                    window.location.reload();
                }
            } catch (err) {
                console.warn('Snapshot refresh failed', err);
            } finally {
                snapshotPending = false;
            }
        }

        if (messagesModalEl) {
            messagesModalEl.addEventListener('show.bs.modal', () => loadPlayerMessages(true));
        }

        refreshSnapshot();
        window.setInterval(refreshSnapshot, 3000);
    }

    function initPrivateNotesSave() {
        const form = document.getElementById('private-notes-form');
        if (!form) {
            return;
        }
        const btn = document.getElementById('save-private-notes-btn');
        const status = document.getElementById('private-notes-status');
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            btn.disabled = true;
            status.textContent = 'Saving...';
            try {
                const res = await fetch(form.action, { method: 'POST', body: new FormData(form) });
                const data = await res.json();
                status.textContent = data.ok ? 'Saved' : 'Failed';
            } catch {
                status.textContent = 'Failed';
            } finally {
                btn.disabled = false;
                setTimeout(() => { status.textContent = ''; }, 2000);
            }
        });
    }

    function initCharacterCreatePage() {
        // Wire up the import JSON button regardless of the current wizard step.
        document.getElementById('import-json-input')?.addEventListener('change', function () {
            if (this.files.length > 0) {
                document.getElementById('import-json-form')?.submit();
            }
        });
        document.getElementById('import-json-trigger')?.addEventListener('click', function () {
            document.getElementById('import-json-input')?.click();
        });

        const config = document.getElementById('character-wizard-config');
        const wizardDataset = config?.dataset || {};
        const WIZ_I18N = {
            noWeapons: wizardDataset.noWeapons || 'No weapons added.',
            noCombatSkill: wizardDataset.noCombatSkill || 'No combat skill',
            preparedBadge: wizardDataset.preparedBadge || 'Prepared',
            defaultBadge: wizardDataset.defaultBadge || 'Default',
            weaponFallback: wizardDataset.weaponFallback || 'Weapon',
            addCustomSkill: wizardDataset.addCustomSkill || 'Add Custom Skill',
            addSkillHelp: wizardDataset.addSkillHelp || '',
            addSkill: wizardDataset.addSkill || 'Add Skill',
            renameCustomSkill: wizardDataset.renameCustomSkill || 'Rename Custom Skill',
            renameSkillHelp: wizardDataset.renameSkillHelp || '',
            updateSkill: wizardDataset.updateSkill || 'Update Skill',
            enterSkillName: wizardDataset.enterSkillName || 'Please enter a skill name',
            skillContainerNotFound: wizardDataset.skillContainerNotFound || 'Skill container not found',
            baseValue: wizardDataset.baseValue || 'base',
            renameSkillTitle: wizardDataset.renameSkillTitle || 'Rename custom skill',
            removeSkillTitle: wizardDataset.removeSkillTitle || 'Remove custom skill',
            editWeapon: wizardDataset.editWeapon || 'Edit Weapon',
            saveWeapon: wizardDataset.saveWeapon || 'Save',
            addWeapon: wizardDataset.addWeapon || 'Add Weapon',
            addWeaponBtn: wizardDataset.addWeaponBtn || 'Add',
            unarmedBrawl: wizardDataset.unarmedBrawl || 'Unarmed Brawl',
            noSpells: wizardDataset.noSpells || 'No spells added.',
            spellFallback: wizardDataset.spellFallback || 'Spell',
            statDescriptions: {
                STR: wizardDataset.statDescStr || '',
                CON: wizardDataset.statDescCon || '',
                DEX: wizardDataset.statDescDex || '',
                INT: wizardDataset.statDescInt || '',
                POW: wizardDataset.statDescPow || '',
                SIZ: wizardDataset.statDescSiz || '',
                APP: wizardDataset.statDescApp || '',
                EDU: wizardDataset.statDescEdu || '',
                LCK: wizardDataset.statDescLck || '',
            },
        };
        const WEAPON_NAME_I18N = { 'Unarmed Brawl': WIZ_I18N.unarmedBrawl };
        const initialWeaponsData = JSON.parse(document.getElementById('initial-weapons')?.textContent || '[]');
        const initialItemsData = JSON.parse(document.getElementById('initial-items')?.textContent || '[]');
        const initialSpellsData = JSON.parse(document.getElementById('initial-spells')?.textContent || '[]');
        const customSkillsScript = document.getElementById('initial-custom-skills');
        const state = window.characterWizardState = {
            weaponEntries: Array.isArray(initialWeaponsData) ? initialWeaponsData : [],
            itemEntries: Array.isArray(initialItemsData) ? initialItemsData : [],
            spellEntries: Array.isArray(initialSpellsData) ? initialSpellsData : [],
            editingWeaponIndex: null,
            editingItemIndex: null,
            currentSkillCategory: '',
            editingCustomSkillId: null,
            customSkillEntries: customSkillsScript ? JSON.parse(customSkillsScript.textContent || '{}') : {},
            WIZ_I18N,
        };

        const weaponList = document.getElementById('weapon-list');
        const itemList = document.getElementById('item-list');
        const spellList = document.getElementById('spell-list');
        const weaponsJsonInput = document.getElementById('weapons_json');
        const itemsJsonInput = document.getElementById('items_json');
        const spellsJsonInput = document.getElementById('spells_json');
        const customSkillsInput = document.getElementById('custom_skills_json');

        function syncInventoryJson() {
            if (weaponsJsonInput) weaponsJsonInput.value = JSON.stringify(state.weaponEntries);
            if (itemsJsonInput) itemsJsonInput.value = JSON.stringify(state.itemEntries);
            if (spellsJsonInput) spellsJsonInput.value = JSON.stringify(state.spellEntries);
        }

        function syncCustomSkillsJson() {
            if (customSkillsInput) {
                customSkillsInput.value = JSON.stringify(state.customSkillEntries);
            }
        }

        function renderWeapons() {
            if (!weaponList) return;
            weaponList.innerHTML = '';
            if (!state.weaponEntries.length) {
                weaponList.innerHTML = `<div class="list-group-item text-muted">${WIZ_I18N.noWeapons}</div>`;
                syncInventoryJson();
                return;
            }
            state.weaponEntries.forEach((entry, index) => {
                const name = entry.custom_name || entry.name || `${WIZ_I18N.weaponFallback} #${index + 1}`;
                const displayName = WEAPON_NAME_I18N[name] || name;
                const damage = entry.damage || '1D4';
                const skillName = entry.skill_name || WIZ_I18N.noCombatSkill;
                const prepared = entry.is_prepared ? ` <span class="badge text-bg-info">${WIZ_I18N.preparedBadge}</span>` : '';
                const actions = entry.is_default_unarmed
                    ? `<span class="badge text-bg-secondary">${WIZ_I18N.defaultBadge}</span>`
                    : `<div class="d-flex gap-1">
                            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="editWeapon(${index})"><i class="fas fa-pen"></i></button>
                            <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeWeapon(${index})"><i class="fas fa-trash"></i></button>
                       </div>`;
                weaponList.innerHTML += `<div class="list-group-item d-flex justify-content-between align-items-center gap-2">
                    <span><strong>${displayName}</strong> <span class="text-muted">(${damage})</span> &middot; ${skillName}${prepared}</span>
                    ${actions}
                </div>`;
            });
            syncInventoryJson();
        }

        function renderItems() {
            if (!itemList) return;
            itemList.innerHTML = '';
            if (!state.itemEntries.length) {
                itemList.innerHTML = '<div class="list-group-item text-muted">No items added.</div>';
                syncInventoryJson();
                return;
            }
            state.itemEntries.forEach((entry, index) => {
                if (state.editingItemIndex === index) {
                    itemList.innerHTML += `<div class="list-group-item">
                        <div class="d-flex gap-2 align-items-center">
                            <input type="text" class="form-control form-control-sm" id="edit-item-name-${index}" value="${escapeHtmlAttr(entry.custom_name || entry.name || '')}">
                            <input type="number" min="1" class="form-control form-control-sm" style="width:80px" id="edit-item-qty-${index}" value="${escapeHtmlAttr(entry.quantity)}">
                            <button type="button" class="btn btn-sm btn-success" onclick="saveEditItem(${index})"><i class="fas fa-check"></i></button>
                            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="cancelEditItem()"><i class="fas fa-times"></i></button>
                        </div>
                    </div>`;
                } else {
                    const name = entry.custom_name || entry.name || `Item #${index + 1}`;
                    itemList.innerHTML += `<div class="list-group-item d-flex justify-content-between align-items-center">
                        <span>${escapeHtml(name)} <span class="badge text-bg-secondary">×${entry.quantity}</span></span>
                        <div class="d-flex gap-1">
                            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="editItem(${index})"><i class="fas fa-pen"></i></button>
                            <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeItem(${index})"><i class="fas fa-trash"></i></button>
                        </div>
                    </div>`;
                }
            });
            syncInventoryJson();
        }

        function renderSpells() {
            if (!spellList) return;
            spellList.innerHTML = '';
            if (!state.spellEntries.length) {
                spellList.innerHTML = `<div class="list-group-item text-muted">${WIZ_I18N.noSpells}</div>`;
                syncInventoryJson();
                return;
            }
            state.spellEntries.forEach((entry, index) => {
                const spellName = entry.name || `${WIZ_I18N.spellFallback} #${index + 1}`;
                const badgeColor = entry.badge_color || 'bg-info';
                spellList.innerHTML += `<div class="list-group-item d-flex justify-content-between align-items-center">
                    <span class="badge ${badgeColor}">${escapeHtml(spellName)}</span>
                    <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeSpell(${index})"><i class="fas fa-trash"></i></button>
                </div>`;
            });
            syncInventoryJson();
        }

        window.removeItem = function removeItem(index) {
            state.itemEntries.splice(index, 1);
            renderItems();
        };

        window.removeSpell = function removeSpell(index) {
            state.spellEntries.splice(index, 1);
            renderSpells();
        };

        window.editWeapon = function editWeapon(index) {
            const entry = state.weaponEntries[index];
            state.editingWeaponIndex = index;
            document.getElementById('weaponModalTitle').textContent = WIZ_I18N.editWeapon;
            document.getElementById('confirm-weapon-btn').textContent = WIZ_I18N.saveWeapon;
            document.getElementById('weapon-template-select').value = entry.weapon_id || '';
            document.getElementById('weapon-custom-name').value = entry.custom_name || entry.name || '';
            document.getElementById('weapon-custom-damage').value = entry.damage || '';
            const skillSelect = document.getElementById('weapon-skill-select');
            const matchedOption = Array.from(skillSelect.options).find((o) => Number(o.value) === entry.skill_id);
            skillSelect.value = matchedOption ? matchedOption.value : '';
            bootstrap.Modal.getOrCreateInstance(document.getElementById('weaponModal')).show();
        };

        window.editItem = function editItem(index) {
            state.editingItemIndex = index;
            renderItems();
            const nameInput = document.getElementById(`edit-item-name-${index}`);
            if (nameInput) nameInput.focus();
        };

        window.saveEditItem = function saveEditItem(index) {
            const nameInput = document.getElementById(`edit-item-name-${index}`);
            const qtyInput = document.getElementById(`edit-item-qty-${index}`);
            const newName = nameInput ? nameInput.value.trim() : '';
            const newQty = qtyInput ? Number(qtyInput.value) : 1;
            if (!newName || newQty <= 0) return;
            state.itemEntries[index].custom_name = newName;
            state.itemEntries[index].name = newName;
            state.itemEntries[index].quantity = newQty;
            state.editingItemIndex = null;
            renderItems();
        };

        window.cancelEditItem = function cancelEditItem() {
            state.editingItemIndex = null;
            renderItems();
        };

        function resetWeaponModal() {
            state.editingWeaponIndex = null;
            document.getElementById('weaponModalTitle').textContent = WIZ_I18N.addWeapon;
            document.getElementById('confirm-weapon-btn').textContent = WIZ_I18N.addWeaponBtn;
            document.getElementById('weapon-template-select').value = '';
            document.getElementById('weapon-custom-name').value = '';
            document.getElementById('weapon-custom-damage').value = '';
            document.getElementById('weapon-skill-select').value = '';
        }

        function getNextCustomSkillId() {
            const existingIds = Object.keys(state.customSkillEntries).map(k => parseInt(k, 10)).filter(n => !isNaN(n) && n < 0);
            return String(existingIds.length > 0 ? Math.min(...existingIds) - 1 : -1);
        }

        window.setSkillCategory = function setSkillCategory(category) {
            state.editingCustomSkillId = null;
            state.currentSkillCategory = category;
            document.getElementById('new-skill-name').value = '';
            document.getElementById('newSkillModalTitle').textContent = WIZ_I18N.addCustomSkill;
            const helpEl = document.getElementById('newSkillModalHelp');
            if (helpEl) helpEl.textContent = WIZ_I18N.addSkillHelp;
            document.getElementById('confirm-new-skill-text').textContent = WIZ_I18N.addSkill;
        };

        window.editCustomSkill = function editCustomSkill(skillId) {
            const entry = state.customSkillEntries[String(skillId)];
            if (!entry) return;
            state.editingCustomSkillId = String(skillId);
            state.currentSkillCategory = entry.category || 'general';
            document.getElementById('new-skill-name').value = entry.name || '';
            document.getElementById('newSkillModalTitle').textContent = WIZ_I18N.renameCustomSkill;
            const helpEl = document.getElementById('newSkillModalHelp');
            if (helpEl) helpEl.textContent = WIZ_I18N.renameSkillHelp;
            document.getElementById('confirm-new-skill-text').textContent = WIZ_I18N.updateSkill;
            bootstrap.Modal.getOrCreateInstance(document.getElementById('newSkillModal')).show();
        };

        window.removeCustomSkill = function removeCustomSkill(skillId) {
            const element = document.getElementById(`custom-skill-${skillId}`);
            delete state.customSkillEntries[String(skillId)];
            if (element) element.remove();
            syncCustomSkillsJson();
        };

        window.showWizardStatModal = function showWizardStatModal(statName, statValue) {
            document.getElementById('wizardStatModalTitle').textContent = statName;
            document.getElementById('wizardStatModalValue').textContent = statValue;
            document.getElementById('wizardStatModalDescription').textContent = WIZ_I18N.statDescriptions[statName] || '';
            bootstrap.Modal.getOrCreateInstance(document.getElementById('wizardStatModal')).show();
        };

        document.getElementById('weaponModal')?.addEventListener('hidden.bs.modal', resetWeaponModal);
        document.getElementById('weapon-template-select')?.addEventListener('change', (event) => {
            const selected = event.target.options[event.target.selectedIndex];
            const skillName = selected.dataset.skillName;
            const skillSelect = document.getElementById('weapon-skill-select');
            if (selected.value) {
                document.getElementById('weapon-custom-damage').value = selected.dataset.damage || '';
            }
            if (skillName) {
                const matchedOption = Array.from(skillSelect.options).find((option) => option.dataset.name === skillName);
                if (matchedOption) skillSelect.value = matchedOption.value;
            }
        });
        document.getElementById('confirm-weapon-btn')?.addEventListener('click', () => {
            const select = document.getElementById('weapon-template-select');
            const selected = select.options[select.selectedIndex];
            const customName = document.getElementById('weapon-custom-name').value.trim();
            const customDamage = document.getElementById('weapon-custom-damage').value.trim();
            const skillSelect = document.getElementById('weapon-skill-select');
            const selectedSkill = skillSelect.options[skillSelect.selectedIndex];
            const entry = {
                weapon_id: selected.value ? Number(selected.value) : 0,
                custom_name: selected.value ? '' : customName,
                name: selected.dataset.name || customName,
                damage: selected.dataset.damage || customDamage || '1D4',
                skill_id: selectedSkill.value ? Number(selectedSkill.value) : 0,
                skill_name: selectedSkill.dataset.name || '',
                is_prepared: false,
                is_default_unarmed: false,
            };
            if ((!entry.weapon_id && !entry.custom_name) || !entry.skill_id) return;
            if (state.editingWeaponIndex !== null) {
                state.weaponEntries[state.editingWeaponIndex] = { ...state.weaponEntries[state.editingWeaponIndex], ...entry };
            } else {
                state.weaponEntries.push(entry);
            }
            renderWeapons();
            bootstrap.Modal.getInstance(document.getElementById('weaponModal'))?.hide();
        });
        document.getElementById('confirm-add-item')?.addEventListener('click', () => {
            const customName = document.getElementById('inline-item-name').value.trim();
            const quantity = Number(document.getElementById('inline-item-quantity').value || 1);
            if (!customName || quantity <= 0) return;
            state.itemEntries.push({ item_id: 0, custom_name: customName, name: customName, quantity });
            renderItems();
            document.getElementById('inline-item-name').value = '';
            document.getElementById('inline-item-quantity').value = '1';
        });
        document.getElementById('confirm-add-spell')?.addEventListener('click', () => {
            const select = document.getElementById('spell-template-select');
            if (!select) return;
            const selected = select.options[select.selectedIndex];
            if (!selected || !selected.value) return;
            const spellId = Number(selected.value);
            if (state.spellEntries.some((entry) => Number(entry.spell_id) === spellId)) {
                return;
            }
            state.spellEntries.push({
                spell_id: spellId,
                name: selected.dataset.name || selected.textContent,
                badge_color: selected.dataset.color || 'bg-info',
            });
            renderSpells();
            select.value = '';
        });
        document.getElementById('inline-item-name')?.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                document.getElementById('confirm-add-item')?.click();
            }
        });
        document.getElementById('confirm-new-skill-btn')?.addEventListener('click', () => {
            const skillName = document.getElementById('new-skill-name').value.trim();
            if (!skillName) {
                window.alert(WIZ_I18N.enterSkillName);
                return;
            }
            if (state.editingCustomSkillId) {
                state.customSkillEntries[state.editingCustomSkillId] = {
                    ...state.customSkillEntries[state.editingCustomSkillId],
                    name: skillName,
                    category: state.currentSkillCategory || state.customSkillEntries[state.editingCustomSkillId].category || 'general',
                    description: `Custom skill: ${skillName}`,
                };
                const existingRow = document.getElementById(`custom-skill-${state.editingCustomSkillId}`);
                const nameElement = existingRow?.querySelector('.skill-editor-name');
                if (nameElement) nameElement.textContent = skillName;
            } else {
                const customSkillId = getNextCustomSkillId();
                const container = document.getElementById(`skills_${state.currentSkillCategory}`);
                if (!container) {
                    window.alert(WIZ_I18N.skillContainerNotFound);
                    return;
                }
                const colDiv = document.createElement('div');
                colDiv.className = 'skill-editor-item';
                colDiv.id = `custom-skill-${customSkillId}`;
                colDiv.dataset.customSkillId = customSkillId;
                state.customSkillEntries[customSkillId] = {
                    name: skillName,
                    category: state.currentSkillCategory || 'general',
                    base_value: 1,
                    description: `Custom skill: ${skillName}`,
                };
                colDiv.innerHTML = `
                    <div class="skill-editor-meta">
                        <label class="skill-editor-label" for="skill_${customSkillId}">
                            <span class="skill-editor-name">${escapeHtml(skillName)}</span>
                            <span class="skill-editor-base">${WIZ_I18N.baseValue} 1%</span>
                        </label>
                    </div>
                    <div class="skill-editor-controls">
                        <button type="button" class="skill-action-btn skill-edit-btn" onclick="editCustomSkill('${customSkillId}')" title="${escapeHtmlAttr(WIZ_I18N.renameSkillTitle)}">
                            <i class="fas fa-pen"></i>
                        </button>
                        <button type="button" class="skill-remove-btn skill-action-btn" onclick="removeCustomSkill('${customSkillId}')" title="${escapeHtmlAttr(WIZ_I18N.removeSkillTitle)}">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                        <input id="skill_${customSkillId}" type="number" min="0" max="100" class="form-control form-control-sm skill-editor-input" name="skill_${customSkillId}" value="1">
                    </div>
                `;
                container.appendChild(colDiv);
            }
            state.editingCustomSkillId = null;
            syncCustomSkillsJson();
            bootstrap.Modal.getInstance(document.getElementById('newSkillModal'))?.hide();
        });
        syncCustomSkillsJson();
        renderWeapons();
        renderItems();
        renderSpells();
    }

    function initKeeperMessagesPanel(configEl) {
        const form = document.getElementById('keeper-message-form');
        const list = document.getElementById('keeper-messages-list');
        if (!form || !list) return;
        if (form.dataset.ajaxBound === '1') return;

        const status = document.getElementById('keeper-message-status');
        const recipientSelect = document.getElementById('keeper-recipient');
        const contentInput = document.getElementById('keeper-message-content');
        const cfg = configEl || document.getElementById('scenario-manage-config');
        const messagesUrl = cfg?.dataset.messagesUrl || '';
        if (!messagesUrl) {
            console.warn('Keeper messages URL is missing from page config.');
            return;
        }

        function activateMessagesTab() {
            if (!window.bootstrap?.Tab) return;
            const tabTrigger = document.querySelector('#manageTabs .nav-link[href="#tab-messages"]');
            if (tabTrigger) {
                new bootstrap.Tab(tabTrigger).show();
            }
        }

        function setStatus(text) {
            if (status) status.textContent = text || '';
        }

        function renderMessages(messages) {
            if (!messages || !messages.length) {
                list.innerHTML = '<div class="text-center text-muted py-4"><i class="fas fa-comment-slash mb-2"></i><div>No messages yet</div></div>';
                return;
            }
            list.innerHTML = messages.map((msg) => `
                <div class="session-message-item p-2 mb-2">
                    <div class="session-message-meta d-flex justify-content-between align-items-center mb-1">
                        <span><strong>${escapeHtml(msg.sender)}</strong> · Private to ${escapeHtml(msg.recipient || 'player')}</span>
                        <span>${new Date(msg.sent_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                    <div class="session-message-content">${escapeHtml(msg.content)}</div>
                </div>
            `).join('');
        }

        let messagesPending = false;
        async function loadMessages(force = false) {
            if (messagesPending && !force) return;
            messagesPending = true;
            try {
                const res = await fetch(messagesUrl, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    cache: 'no-store',
                    credentials: 'same-origin',
                });
                if (!res.ok) {
                    console.warn(`Failed to load keeper messages: HTTP ${res.status}`);
                    return;
                }
                const data = await res.json();
                if (!data.ok) return;
                renderMessages(data.messages || []);
            } catch (err) {
                console.warn('Failed to load keeper messages', err);
            } finally {
                messagesPending = false;
            }
        }

        form.dataset.ajaxBound = '1';
        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            event.stopPropagation();
            setStatus('Sending...');
            if (!recipientSelect?.value) {
                setStatus('Choose a player for a private message.');
                return;
            }
            try {
                const res = await fetch(form.action, {
                    method: 'POST',
                    body: new FormData(form),
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    cache: 'no-store',
                    credentials: 'same-origin',
                });
                if (!res.ok) {
                    setStatus(`Failed to send message (HTTP ${res.status}).`);
                    return;
                }
                const data = await res.json();
                if (!data.ok) {
                    setStatus(data.error || 'Failed to send message.');
                    return;
                }
                if (contentInput) contentInput.value = '';
                if (recipientSelect) recipientSelect.value = '';
                setStatus('Message sent.');
                activateMessagesTab();
                await loadMessages(true);
                setTimeout(() => { setStatus(''); }, 2000);
            } catch {
                setStatus('Failed to send message.');
            }
        });

        loadMessages(true);
        if (list.dataset.pollingBound !== '1') {
            list.dataset.pollingBound = '1';
            window.setInterval(loadMessages, 5000);
        }
    }

    function initScenarioManagePage() {
        const config = document.getElementById('scenario-manage-config');
        if (!config) {
            return;
        }
        const scenarioId = safeNumber(config.dataset.scenarioId, 0);
        let npcTemplatesData = [];
        try {
            const rawTemplatesPayload = document.getElementById('scenario-manage-npc-templates')?.textContent || '[]';
            const parsedTemplates = JSON.parse(rawTemplatesPayload);
            if (Array.isArray(parsedTemplates)) {
                npcTemplatesData = parsedTemplates;
            } else if (typeof parsedTemplates === 'string') {
                const reparsedTemplates = JSON.parse(parsedTemplates);
                npcTemplatesData = Array.isArray(reparsedTemplates) ? reparsedTemplates : [];
            }
        } catch (error) {
            console.warn('Failed to parse NPC templates payload', error);
            npcTemplatesData = [];
        }
        const tplMap = {};
        npcTemplatesData.forEach((t) => { tplMap[t.id] = t; });
        const STORAGE_KEY = config.dataset.storageKey || '';
        function safeStorageGet(key) {
            if (!key) return null;
            try {
                return localStorage.getItem(key);
            } catch {
                return null;
            }
        }
        function safeStorageSet(key, value) {
            if (!key || !value) return;
            try {
                localStorage.setItem(key, value);
            } catch {
                // localStorage may be blocked by browser privacy settings.
            }
        }
        function activateTabByHref(tabHref) {
            if (!tabHref || !window.bootstrap?.Tab) return false;
            const el = document.querySelector(`#manageTabs .nav-link[href="${tabHref}"]`);
            if (!el) return false;
            new bootstrap.Tab(el).show();
            return true;
        }
        const hashTab = (window.location.hash || '').trim();
        const savedTab = safeStorageGet(STORAGE_KEY);
        if (!activateTabByHref(hashTab)) {
            activateTabByHref(savedTab);
        }
        document.querySelectorAll('#manageTabs .nav-link').forEach((el) => {
            el.addEventListener('shown.bs.tab', (e) => {
                const tabHref = e.target.getAttribute('href');
                if (!tabHref) return;
                safeStorageSet(STORAGE_KEY, tabHref);
            });
        });

        async function copyTextToClipboard(text) {
            if (!text) return false;
            if (navigator.clipboard && window.isSecureContext) {
                try {
                    await navigator.clipboard.writeText(text);
                    return true;
                } catch (error) {
                    // fallback below
                }
            }
            try {
                const tempInput = document.createElement('textarea');
                tempInput.value = text;
                tempInput.setAttribute('readonly', 'readonly');
                tempInput.style.position = 'fixed';
                tempInput.style.left = '-9999px';
                document.body.appendChild(tempInput);
                tempInput.focus();
                tempInput.select();
                const copied = document.execCommand('copy');
                document.body.removeChild(tempInput);
                return copied;
            } catch {
                return false;
            }
        }

        function setCopyButtonState(btn, iconClass, titleText) {
            btn.innerHTML = `<i class="${iconClass}"></i>`;
            btn.title = titleText;
        }

        document.querySelectorAll('.copy-btn').forEach((btn) => {
            btn.addEventListener('click', async () => {
                const originalTitle = btn.title || 'Copy invite link';
                const copied = await copyTextToClipboard(btn.dataset.url || '');
                if (copied) {
                    setCopyButtonState(btn, 'fas fa-check', 'Copied');
                } else {
                    setCopyButtonState(btn, 'fas fa-exclamation-triangle', 'Copy failed. Copy manually from the link text.');
                }
                setTimeout(() => {
                    setCopyButtonState(btn, 'fas fa-copy', originalTitle);
                }, 2000);
            });
        });

        const qrModal = document.getElementById('qrModal');
        if (qrModal) {
            qrModal.addEventListener('show.bs.modal', async (e) => {
                const btn = e.relatedTarget;
                const url = btn ? btn.dataset.inviteUrl : '';
                const container = document.getElementById('qrcode');
                if (!container) return;
                container.innerHTML = '';
                if (!url) return;
                try {
                    if (!window.QRCode) {
                        await loadExternalScript(config.dataset.qrcodeSrc || '');
                    }
                    if (window.QRCode) {
                        new QRCode(container, {
                            text: url,
                            width: 200,
                            height: 200,
                            colorDark: '#000000',
                            colorLight: '#ffffff',
                            correctLevel: QRCode.CorrectLevel.H,
                        });
                    }
                } catch (err) {
                    container.innerHTML = '<div class="text-danger small">Failed to load QR code generator.</div>';
                }
            });
        }

        function clampCardPercent(value, maxValue) {
            return Math.max(0, Math.min(100, (value / Math.max(maxValue, 1)) * 100));
        }

        function patchCardResource(sheet, resource, current, maxValue) {
            const container = sheet.querySelector(`.stat-bar-container[data-resource="${resource}"]`);
            if (container) {
                container.dataset.current = current;
                container.dataset.max = maxValue;
            }
            const fill = sheet.querySelector(`[data-resource-fill="${resource}"]`);
            if (fill) fill.style.width = `${clampCardPercent(current, maxValue)}%`;
            const text = sheet.querySelector(`[data-resource-text="${resource}"]`);
            if (text) text.textContent = maxValue != null ? `${current}/${maxValue}` : `${current}`;
        }

        function renderEffectsBadges(characterId, effects) {
            const container = document.getElementById(`effects-badges-${characterId}`);
            if (!container) return;
            if (!effects || !effects.length) {
                container.innerHTML = '';
                return;
            }
            container.innerHTML = effects
                .map((effect) => `<span class="badge ${escapeHtmlAttr(effect.badge_color)} effect-badge" data-effect-description="${escapeHtmlAttr(effect.description)}" role="button" tabindex="0">${escapeHtmlAttr(effect.name)}</span>`)
                .join('');
            if (typeof window.initEffectBadgePopovers === 'function') window.initEffectBadgePopovers(container);
        }

        function patchUpdatedCards(cards) {
            (cards || []).forEach((card) => {
                const sheet = document.querySelector(`.character-sheet[data-character-id="${card.character_id}"]`);
                if (!sheet || !card.resources) return;
                if (card.resources.hp) patchCardResource(sheet, 'hp', card.resources.hp.current, card.resources.hp.max);
                if (card.resources.sanity) patchCardResource(sheet, 'sanity', card.resources.sanity.current, card.resources.sanity.max);
                if (card.resources.mp) patchCardResource(sheet, 'mp', card.resources.mp.current, card.resources.mp.max);
                if (card.resources.luck) patchCardResource(sheet, 'luck', card.resources.luck.current, card.resources.luck.max);
                renderEffectsBadges(card.character_id, card.effects || []);
                const wrapper = sheet.closest('.cast-wrapper');
                if (wrapper && typeof card.is_alive === 'boolean') {
                    wrapper.classList.toggle('dead-card', !card.is_alive);
                }
            });
        }

        function applyTimeUpdateResponse(data) {
            if (!data || !data.ok) return;
            const timeText = document.getElementById('game-time-text');
            const dayText = document.getElementById('game-day-text');
            if (timeText) timeText.textContent = data.in_game_time;
            if (dayText) dayText.textContent = `Day ${data.in_game_day}`;
            if (Array.isArray(data.updated_cards) && data.updated_cards.length) {
                patchUpdatedCards(data.updated_cards);
            }
        }

        document.querySelectorAll('.time-advance-form').forEach((form) => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const res = await fetch(form.action, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    body: new FormData(form),
                });
                const data = await res.json();
                applyTimeUpdateResponse(data);
            });
        });

        const setTimeForm = document.getElementById('set-time-form');
        if (setTimeForm) {
            setTimeForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const res = await fetch(setTimeForm.action, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    body: new FormData(setTimeForm),
                });
                const data = await res.json();
                applyTimeUpdateResponse(data);
            });
        }

        const notesForm = document.getElementById('notesForm');
        if (notesForm) {
            notesForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const btn = document.getElementById('saveNotesBtn');
                const status = document.getElementById('saveStatus');
                btn.disabled = true;
                const res = await fetch(notesForm.action, {
                    method: 'POST',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    body: new FormData(notesForm),
                });
                const data = await res.json();
                btn.disabled = false;
                if (data.ok) {
                    status.textContent = '✓ Saved';
                    setTimeout(() => { status.textContent = ''; }, 3000);
                }
            });
        }

        window.toggleSkillNeedsUpdate = async function toggleSkillNeedsUpdate(checkbox) {
            const characterId = checkbox.dataset.characterId;
            const skillId = checkbox.dataset.skillId;
            const url = `/scenarios/${scenarioId}/character/${characterId}/skill/${skillId}/needs-update/`;
            const fd = new FormData();
            fd.append('csrfmiddlewaretoken', getCookie('csrftoken'));
            try {
                const res = await fetch(url, { method: 'POST', body: fd });
                const data = await res.json();
                if (!data.ok) checkbox.checked = !checkbox.checked;
            } catch {
                checkbox.checked = !checkbox.checked;
            }
        };

        const tplSearch = document.getElementById('tplSearch');
        const tplList = document.getElementById('tplList');
        const tplIdInput = document.getElementById('tplIdInput');
        const tplAddBtn = document.getElementById('tplAddBtn');
        const tplPreviewBtn = document.getElementById('tplPreviewBtn');
        let selectedTplId = null;

        function selectTemplate(id) {
            selectedTplId = id;
            if (tplIdInput) tplIdInput.value = id;
            if (tplAddBtn) tplAddBtn.disabled = false;
            if (tplPreviewBtn) tplPreviewBtn.disabled = false;
            document.querySelectorAll('.tpl-option').forEach((o) => o.classList.remove('selected'));
            const el = document.querySelector(`.tpl-option[data-id="${id}"]`);
            if (el) el.classList.add('selected');
        }

        if (tplList) {
            tplList.addEventListener('click', (e) => {
                const opt = e.target.closest('.tpl-option');
                if (opt) selectTemplate(Number(opt.dataset.id));
            });
        }
        if (tplSearch) {
            tplSearch.addEventListener('input', () => {
                const q = tplSearch.value.toLowerCase();
                document.querySelectorAll('.tpl-option').forEach((opt) => {
                    opt.style.display = opt.dataset.name.toLowerCase().includes(q) ? '' : 'none';
                });
            });
        }

        function buildPreviewHtml(tpl) {
            const stats = tpl.stats || {};
            const statHtml = Object.entries(stats).map(([k, v]) => `<span class="stat-mini">${escapeHtmlAttr(k)} ${escapeHtmlAttr(String(v))}</span>`).join(' ');
            return `
                <h5 class="text-warning">${escapeHtmlAttr(tpl.name)}</h5>
                ${tpl.occupation ? `<p class="text-muted mb-1"><em>${escapeHtmlAttr(tpl.occupation)}</em></p>` : ''}
                ${tpl.description ? `<p class="small mb-3">${escapeHtmlAttr(tpl.description)}</p>` : ''}
                <div class="row g-2 mb-3">
                    <div class="col-4 text-center"><div class="fw-bold text-danger">${escapeHtmlAttr(String(tpl.hp_current))}/${escapeHtmlAttr(String(tpl.hp_max))}</div><small class="text-muted">HP</small></div>
                    <div class="col-4 text-center"><div class="fw-bold text-success">${escapeHtmlAttr(String(tpl.san_max))}</div><small class="text-muted">SAN max</small></div>
                    <div class="col-4 text-center"><div class="fw-bold text-primary">${escapeHtmlAttr(String(tpl.mp_max))}</div><small class="text-muted">MP max</small></div>
                </div>
                <div>${statHtml}</div>`;
        }

        if (tplPreviewBtn) {
            tplPreviewBtn.addEventListener('click', () => {
                if (!selectedTplId || !tplMap[selectedTplId]) return;
                const tpl = tplMap[selectedTplId];
                document.getElementById('previewModalTitle').textContent = tpl.name;
                document.getElementById('previewModalBody').innerHTML = buildPreviewHtml(tpl);
            });
        }
        document.getElementById('modalAddBtn')?.addEventListener('click', () => {
            bootstrap.Modal.getInstance(document.getElementById('npcPreviewModal'))?.hide();
            document.getElementById('tplForm')?.submit();
        });

        (function initSessionStatBars() {
            const CSRF = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
            function getSheet(el) {
                return el.closest('.character-sheet[data-adjust-url]');
            }
            function updateDisplay(sheet, resource, current, max) {
                const fill = sheet.querySelector(`[data-resource-fill="${resource}"]`);
                const text = sheet.querySelector(`[data-resource-text="${resource}"]`);
                if (fill) fill.style.width = `${clamp((current / Math.max(max, 1)) * 100, 0, 100)}%`;
                if (text) text.textContent = max != null ? `${current}/${max}` : `${current}/100`;
            }
            async function commitStat(sheet, resource, value) {
                const url = sheet.dataset.adjustUrl;
                if (!url) return;
                const body = new FormData();
                body.append('csrfmiddlewaretoken', CSRF);
                body.append(resource, value);
                try {
                    const res = await fetch(url, { method: 'POST', body });
                    const data = await res.json();
                    if (data.ok) {
                        const container = sheet.querySelector(`.stat-bar-container[data-resource="${resource}"]`);
                        if (container) container.dataset.current = value;
                    }
                } catch (e) {
                    console.warn('Stat save failed', e);
                }
            }
            function valueFromClientX(bar, clientX) {
                const container = bar.closest('.stat-bar-container');
                if (!container) return null;
                const max = Number(container.dataset.max || 0);
                const rect = bar.getBoundingClientRect();
                if (!rect.width) return null;
                return Math.round(clamp((clientX - rect.left) / rect.width, 0, 1) * max);
            }
            let dragBar = null;
            let dragPending = null;
            function handleDrag(bar, clientX) {
                const sheet = getSheet(bar);
                if (!sheet) return;
                const resource = bar.dataset.adjustTarget;
                const container = bar.closest('.stat-bar-container');
                if (!resource || !container) return;
                const max = Number(container.dataset.max || 0);
                const val = valueFromClientX(bar, clientX);
                if (val === null) return;
                updateDisplay(sheet, resource, val, max);
                dragPending = { sheet, resource, val };
            }
            function bindAdjustableBars(rootEl) {
                (rootEl || document).querySelectorAll('.character-sheet[data-adjust-url] .stat-bar-adjustable').forEach((bar) => {
                    if (bar.dataset.adjustBound === '1') return;
                    bar.dataset.adjustBound = '1';
                    bar.style.cursor = 'ew-resize';
                    bar.addEventListener('mousedown', (e) => { dragBar = bar; handleDrag(bar, e.clientX); e.preventDefault(); });
                    bar.addEventListener('touchstart', (e) => {
                        const t = e.touches[0];
                        if (t) { dragBar = bar; handleDrag(bar, t.clientX); }
                    }, { passive: true });
                });
            }
            bindAdjustableBars(document);
            window.initAdjustableStatBars = bindAdjustableBars;
            document.addEventListener('mousemove', (e) => { if (dragBar) handleDrag(dragBar, e.clientX); });
            document.addEventListener('touchmove', (e) => {
                if (dragBar) {
                    const t = e.touches[0];
                    if (t) handleDrag(dragBar, t.clientX);
                }
            }, { passive: true });
            function stopDrag() {
                if (dragPending) {
                    commitStat(dragPending.sheet, dragPending.resource, dragPending.val);
                    dragPending = null;
                }
                dragBar = null;
            }
            document.addEventListener('mouseup', stopDrag);
            document.addEventListener('touchend', stopDrag);
        }());

        (function initAliveToggleButtons() {
            const CSRF = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
            function renderAliveState(btn, isAlive) {
                const wrapper = btn.closest('.cast-wrapper');
                if (wrapper) wrapper.classList.toggle('dead-card', !isAlive);
                btn.classList.toggle('btn-outline-danger', isAlive);
                btn.classList.toggle('btn-outline-success', !isAlive);
                btn.title = isAlive ? 'Mark dead' : 'Mark alive';
                btn.innerHTML = isAlive ? '<i class="fas fa-skull-crossbones"></i>' : '<i class="fas fa-heart"></i>';
            }
            document.querySelectorAll('.toggle-alive-btn[data-toggle-alive-url]').forEach((btn) => {
                btn.addEventListener('click', async () => {
                    if (btn.disabled) return;
                    btn.disabled = true;
                    try {
                        const body = new FormData();
                        body.append('csrfmiddlewaretoken', CSRF);
                        const res = await fetch(btn.dataset.toggleAliveUrl, { method: 'POST', body });
                        const data = await res.json();
                        if (data.ok) renderAliveState(btn, data.is_alive);
                    } catch (e) {
                        console.warn('Alive toggle failed', e);
                    } finally {
                        btn.disabled = false;
                    }
                });
            });
        }());

        (function initFightTab() {
            const addSelect = document.getElementById('fight-add-character');
            const addBtn = document.getElementById('fight-add-btn');
            const startBtn = document.getElementById('fight-start-btn');
            const endBtn = document.getElementById('fight-end-btn');
            const nextRoundBtn = document.getElementById('fight-next-round-btn');
            const resetRoundsBtn = document.getElementById('fight-reset-rounds-btn');
            const roundChip = document.getElementById('fight-round-chip');
            const statusEl = document.getElementById('fight-status');
            const listEl = document.getElementById('fight-list');
            const emptyEl = document.getElementById('fight-empty');
            if (!addSelect || !addBtn || !startBtn || !endBtn || !nextRoundBtn || !resetRoundsBtn || !roundChip || !listEl || !emptyEl) return;
            const CSRF = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
            const stateUrl = config.dataset.fightStateUrl || '';
            const startUrl = config.dataset.fightStartUrl || '';
            const endUrl = config.dataset.fightEndUrl || '';
            const addUrl = config.dataset.fightAddUrl || '';
            const removeUrlTemplate = config.dataset.fightRemoveTemplate || '';
            const preparedUrlTemplate = config.dataset.fightPreparedTemplate || '';
            const nextTurnUrl = config.dataset.fightNextUrl || '';
            const resetTurnsUrl = config.dataset.fightResetUrl || '';
            const toggleAliveUrlTemplate = config.dataset.characterToggleAliveTemplate || '';
            function setStatus(msg, isError = false) {
                statusEl.textContent = msg || '';
                statusEl.classList.toggle('text-danger', !!isError);
            }
            function participantUrl(template, participantId) {
                return template.replace('/0/', `/${participantId}/`);
            }
            function characterUrl(template, characterId) {
                return template.replace('/0/', `/${characterId}/`);
            }
            function applyFightSheetMode(participantId) {
                const skillsContent = document.getElementById(`fight-sheet-${participantId}-skills-content`);
                const skillsIcon = document.getElementById(`fight-sheet-${participantId}-skills-icon`);
                const combatContent = document.getElementById(`fight-sheet-${participantId}-combat-content`);
                const combatIcon = document.getElementById(`fight-sheet-${participantId}-combat-icon`);
                if (skillsContent) skillsContent.classList.remove('show');
                if (skillsIcon) { skillsIcon.classList.remove('fa-chevron-up'); skillsIcon.classList.add('fa-chevron-down'); }
                if (combatContent) combatContent.classList.add('show');
                if (combatIcon) { combatIcon.classList.remove('fa-chevron-down'); combatIcon.classList.add('fa-chevron-up'); }
            }
            function renderFightState(state) {
                const active = !!state.active;
                const participants = Array.isArray(state.participants) ? state.participants : [];
                const available = Array.isArray(state.available) ? state.available : [];
                const roundNumber = Number(state.round_number || 0);
                addSelect.innerHTML = '<option value="">Choose participant...</option>' + available.map((entry) => `<option value="${entry.character_id}">${escapeHtmlAttr(entry.label)}</option>`).join('');
                // Adding the first participant can implicitly start the encounter.
                addBtn.disabled = available.length === 0;
                startBtn.disabled = active;
                endBtn.disabled = !active;
                nextRoundBtn.disabled = !active;
                resetRoundsBtn.disabled = !active;
                roundChip.textContent = `Round ${roundNumber}`;
                emptyEl.style.display = active && participants.length ? 'none' : '';
                listEl.innerHTML = participants.map((participant) => `
                    <div class="col-12 col-md-6 col-lg-4 col-xxl-3 fight-card-col" data-fight-participant-id="${participant.participant_id}">
                        <div class="fight-participant ${participant.is_alive ? '' : 'dead-card'}">
                            <div class="fight-header">
                                <div>
                                    <div class="text-warning fw-bold">${escapeHtmlAttr(participant.display_name)}</div>
                                    <div class="fight-dex">DEX ${participant.dex_base} · Effective ${participant.dex_effective}</div>
                                </div>
                                <div class="d-flex gap-2 align-items-center flex-wrap">
                                    <label class="form-check-label small d-flex align-items-center gap-1 text-muted">
                                        <input type="checkbox" class="form-check-input mt-0 fight-prepared-checkbox" data-participant-id="${participant.participant_id}" ${participant.is_weapon_prepared ? 'checked' : ''} ${participant.is_alive ? '' : 'disabled'}>
                                        Prepared weapon
                                    </label>
                                    <button type="button" class="btn btn-sm btn-outline-warning manage-effects-btn" data-character-id="${participant.character_id}" data-character-name="${escapeHtmlAttr(participant.display_name)}" data-bs-toggle="modal" data-bs-target="#effectsManagerModal" title="Manage effects"><i class="fas fa-heartbeat"></i></button>
                                    <button type="button" class="btn btn-sm ${participant.is_alive ? 'btn-outline-danger' : 'btn-outline-success'} fight-toggle-alive-btn" data-character-id="${participant.character_id}" title="${participant.is_alive ? 'Mark dead' : 'Mark alive'}"><i class="fas fa-${participant.is_alive ? 'skull-crossbones' : 'heart'}"></i></button>
                                    <button type="button" class="btn btn-sm btn-outline-light fight-remove-btn" data-participant-id="${participant.participant_id}" title="Remove from fight"><i class="fas fa-user-minus"></i></button>
                                </div>
                            </div>
                            <div class="p-1 card-sheet-wrap">${participant.card_html}</div>
                        </div>
                    </div>
                `).join('');
                participants.forEach((participant) => applyFightSheetMode(participant.participant_id));
                if (typeof window.initAdjustableStatBars === 'function') window.initAdjustableStatBars(listEl);
            }
            async function postAndRender(url, extraFormData) {
                const body = extraFormData || new FormData();
                if (CSRF && !body.get('csrfmiddlewaretoken')) body.append('csrfmiddlewaretoken', CSRF);
                const res = await fetch(url, { method: 'POST', body, headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                const data = await res.json();
                if (!data.ok) throw new Error(data.error || 'Request failed');
                renderFightState(data);
                return data;
            }
            async function loadState() {
                try {
                    const res = await fetch(stateUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                    const data = await res.json();
                    if (!data.ok) return;
                    renderFightState(data);
                } catch {
                    setStatus('Failed to load fight state.', true);
                }
            }
            startBtn.addEventListener('click', async () => { try { setStatus('Starting fight...'); await postAndRender(startUrl); setStatus('Fight mode started.'); } catch (err) { setStatus(err.message, true); } });
            endBtn.addEventListener('click', async () => { if (!window.confirm('End fight and remove all participants?')) return; try { setStatus('Ending fight...'); await postAndRender(endUrl); setStatus('Fight ended.'); } catch (err) { setStatus(err.message, true); } });
            nextRoundBtn.addEventListener('click', async () => { try { await postAndRender(nextTurnUrl); setStatus('Round advanced.'); } catch (err) { setStatus(err.message, true); } });
            resetRoundsBtn.addEventListener('click', async () => { try { await postAndRender(resetTurnsUrl); setStatus('Round counter reset.'); } catch (err) { setStatus(err.message, true); } });
            addBtn.addEventListener('click', async () => {
                const characterId = Number(addSelect.value || 0);
                if (!characterId) { setStatus('Select a participant first.', true); return; }
                const body = new FormData();
                body.append('character_id', String(characterId));
                try { setStatus('Adding participant...'); await postAndRender(addUrl, body); addSelect.value = ''; setStatus('Participant added.'); } catch (err) { setStatus(err.message, true); }
            });
            listEl.addEventListener('change', async (event) => {
                const checkbox = event.target.closest('.fight-prepared-checkbox');
                if (!checkbox) return;
                const participantId = Number(checkbox.dataset.participantId || 0);
                if (!participantId) return;
                const body = new FormData();
                body.append('is_prepared', checkbox.checked ? '1' : '0');
                try { await postAndRender(participantUrl(preparedUrlTemplate, participantId), body); setStatus('Initiative updated.'); } catch (err) { setStatus(err.message, true); }
            });
            listEl.addEventListener('click', async (event) => {
                const removeBtn = event.target.closest('.fight-remove-btn');
                if (removeBtn) {
                    const participantId = Number(removeBtn.dataset.participantId || 0);
                    if (!participantId) return;
                    try { await postAndRender(participantUrl(removeUrlTemplate, participantId)); setStatus('Participant removed from fight.'); } catch (err) { setStatus(err.message, true); }
                    return;
                }
                const toggleAliveBtn = event.target.closest('.fight-toggle-alive-btn');
                if (toggleAliveBtn) {
                    const characterId = Number(toggleAliveBtn.dataset.characterId || 0);
                    if (!characterId) return;
                    try {
                        const body = new FormData();
                        if (CSRF) body.append('csrfmiddlewaretoken', CSRF);
                        const res = await fetch(characterUrl(toggleAliveUrlTemplate, characterId), { method: 'POST', body, headers: { 'X-Requested-With': 'XMLHttpRequest' } });
                        const data = await res.json();
                        if (!data.ok) throw new Error(data.error || 'Failed to toggle state.');
                        await loadState();
                        setStatus('Character state updated.');
                    } catch (err) {
                        setStatus(err.message, true);
                    }
                }
            });
            window.refreshFightState = loadState;
            loadState();
        }());

        (function initEffectsManager() {
            const CSRF = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
            const modalEl = document.getElementById('effectsManagerModal');
            if (!modalEl) return;
            let activeCharacterId = null;
            let activeCharacterName = '';
            const titleEl = document.getElementById('effectsModalTitle');
            const statusEl = document.getElementById('effectsModalStatus');
            const currentListEl = document.getElementById('currentEffectsList');
            const selectEl = document.getElementById('effectSelect');
            const customNameEl = document.getElementById('customEffectName');
            const addSelectedBtn = document.getElementById('addSelectedEffectBtn');
            const addCustomBtn = document.getElementById('addCustomEffectBtn');
            const getUrlTemplate = modalEl.dataset.getUrlTemplate;
            const addUrlTemplate = modalEl.dataset.addUrlTemplate;
            const removeUrlTemplate = modalEl.dataset.removeUrlTemplate;
            function setStatus(msg, isError) {
                statusEl.textContent = msg || '';
                statusEl.classList.toggle('text-danger', Boolean(isError));
            }
            function urlForCharacter(template, characterId) { return template.replace('/0/', `/${characterId}/`); }
            function urlForRemove(characterId, effectId) { return removeUrlTemplate.replace('/0/', `/${characterId}/`).replace('/0/', `/${effectId}/`); }
            function getModalBadgeClass(effect) {
                const colorClass = (effect && effect.badge_color) ? effect.badge_color : 'bg-secondary';
                return colorClass === 'bg-dark' ? 'bg-secondary' : colorClass;
            }
            function formatEffectType(effectType) {
                const labels = { NORMAL: 'Custom status effect', PHOBIA: 'Phobia', MADNESS: 'Madness', MANIA: 'Mania', DEEP_WOUND: 'Deep wound' };
                return labels[effectType] || 'Effect';
            }
            function renderBadges(characterId, effects) {
                const container = document.getElementById(`effects-badges-${characterId}`);
                if (!container) return;
                if (!effects || !effects.length) {
                    container.innerHTML = '';
                    return;
                }
                container.innerHTML = effects.map((effect) => `<span class="badge ${escapeHtmlAttr(effect.badge_color)} effect-badge" data-effect-description="${escapeHtmlAttr(effect.description)}" role="button" tabindex="0">${escapeHtmlAttr(effect.name)}</span>`).join('');
                if (typeof window.initEffectBadgePopovers === 'function') window.initEffectBadgePopovers(container);
            }
            function renderCurrentEffects(effects) {
                if (!effects || !effects.length) {
                    currentListEl.innerHTML = '<p class="mb-0 text-muted">No active effects.</p>';
                    return;
                }
                currentListEl.innerHTML = effects.map((effect) => `
                    <div class="d-flex justify-content-between align-items-center border rounded p-2 mb-2">
                        <div>
                            <span class="badge ${getModalBadgeClass(effect)} me-2 effect-badge" data-effect-description="${escapeHtmlAttr(effect.description)}" role="button" tabindex="0">${escapeHtmlAttr(effect.name)}</span>
                            <small class="effect-type-text">${formatEffectType(effect.effect_type)}</small>
                        </div>
                        <button type="button" class="btn btn-sm btn-outline-danger remove-effect-btn" data-effect-id="${effect.id}"><i class="fas fa-times"></i></button>
                    </div>
                `).join('');
                if (typeof window.initEffectBadgePopovers === 'function') window.initEffectBadgePopovers(currentListEl);
            }
            async function loadEffects() {
                if (!activeCharacterId) return;
                setStatus('Loading...');
                try {
                    const res = await fetch(urlForCharacter(getUrlTemplate, activeCharacterId));
                    const data = await res.json();
                    if (!data.ok) { setStatus(data.error || 'Failed to load effects.', true); return; }
                    renderCurrentEffects(data.effects || []);
                    renderBadges(activeCharacterId, data.effects || []);
                    setStatus('');
                } catch {
                    setStatus('Failed to load effects.', true);
                }
            }
            async function addEffect(payload) {
                if (!activeCharacterId) return;
                setStatus('Saving...');
                const body = new FormData();
                body.append('csrfmiddlewaretoken', CSRF);
                Object.entries(payload).forEach(([k, v]) => body.append(k, v));
                try {
                    const res = await fetch(urlForCharacter(addUrlTemplate, activeCharacterId), { method: 'POST', body });
                    const data = await res.json();
                    if (!data.ok) { setStatus(data.error || 'Failed to add effect.', true); return; }
                    customNameEl.value = '';
                    await loadEffects();
                    if (typeof window.refreshFightState === 'function') window.refreshFightState();
                    setStatus('Effect updated.');
                } catch {
                    setStatus('Failed to add effect.', true);
                }
            }
            async function removeEffect(effectId) {
                if (!activeCharacterId) return;
                const body = new FormData();
                body.append('csrfmiddlewaretoken', CSRF);
                setStatus('Removing...');
                try {
                    const res = await fetch(urlForRemove(activeCharacterId, effectId), { method: 'POST', body });
                    const data = await res.json();
                    if (!data.ok) { setStatus(data.error || 'Failed to remove effect.', true); return; }
                    await loadEffects();
                    if (typeof window.refreshFightState === 'function') window.refreshFightState();
                    setStatus('Effect removed.');
                } catch {
                    setStatus('Failed to remove effect.', true);
                }
            }
            document.addEventListener('click', (event) => {
                const btn = event.target.closest('.manage-effects-btn');
                if (!btn) return;
                activeCharacterId = Number(btn.dataset.characterId);
                activeCharacterName = btn.dataset.characterName || 'Character';
                titleEl.innerHTML = `<i class="fas fa-heartbeat me-2"></i>Manage effects - ${escapeHtmlAttr(activeCharacterName)}`;
                loadEffects();
            });
            addSelectedBtn?.addEventListener('click', () => {
                const effectId = Number(selectEl.value || 0);
                if (!effectId) { setStatus('Choose an effect first.', true); return; }
                addEffect({ effect_id: effectId, remaining_rounds: 1 });
            });
            addCustomBtn?.addEventListener('click', () => {
                const name = (customNameEl.value || '').trim();
                if (!name) { setStatus('Enter a custom effect name.', true); return; }
                addEffect({ effect_name: name, remaining_rounds: 1 });
            });
            currentListEl?.addEventListener('click', (event) => {
                const button = event.target.closest('.remove-effect-btn');
                if (!button) return;
                const effectId = Number(button.dataset.effectId || 0);
                if (!effectId) return;
                removeEffect(effectId);
            });
        }());

        initKeeperMessagesPanel(config);
    }

    function initPageScripts() {
        function safeInit(label, fn) {
            try {
                fn();
            } catch (error) {
                console.error(`Init failed: ${label}`, error);
            }
        }
        if (typeof window.initEffectBadgePopovers === 'function') {
            window.initEffectBadgePopovers(document);
        }
        if (typeof window.initSpellBadgePopups === 'function') {
            window.initSpellBadgePopups();
        }
        safeInit('status adjust controls', initStatusAdjustControls);
        safeInit('character edit page', initCharacterEditPage);
        safeInit('scenario detail page', initScenarioDetailPage);
        safeInit('private notes save', initPrivateNotesSave);
        safeInit('character create page', initCharacterCreatePage);
        safeInit('keeper messages panel', initKeeperMessagesPanel);
        safeInit('scenario manage page', initScenarioManagePage);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPageScripts);
    } else {
        initPageScripts();
    }
}());






