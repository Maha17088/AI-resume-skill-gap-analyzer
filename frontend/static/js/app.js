const API = 'http://localhost:5000/api';
let token = localStorage.getItem('ss_token');
let currentUser = null;
let analysisResult = null;
let currentApp = null;
let suggestedRoleData = null;

// ── LOADER ────────────────────────────────────────────────────────────────────
function showLoader(msg='Processing...'){
  let l=document.getElementById('loader');
  if(!l){
    l=document.createElement('div');
    l.id='loader'; l.className='loader';
    l.innerHTML=`<div class="loader-box"><div class="spinner"></div><div class="loader-txt" id="loader-txt">${msg}</div></div>`;
    document.body.appendChild(l);
  }
  document.getElementById('loader-txt').textContent=msg;
  l.classList.add('active');
}
function hideLoader(){ const l=document.getElementById('loader'); if(l) l.classList.remove('active'); }

// ── API HELPER ────────────────────────────────────────────────────────────────
async function api(path, opts={}){
  const headers = {'Content-Type':'application/json'};
  if(token) headers['Authorization'] = 'Bearer '+token;
  const res = await fetch(API+path, {...opts, headers:{...headers,...(opts.headers||{})}});
  const data = await res.json();
  if(!res.ok) throw new Error(data.error || 'Request failed');
  return data;
}

// ── AUTH ──────────────────────────────────────────────────────────────────────
function switchAuthTab(t){
  document.querySelectorAll('.auth-tab').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.auth-form').forEach(f=>f.classList.remove('active'));
  document.querySelectorAll('.auth-tab')[t==='login'?0:1].classList.add('active');
  document.getElementById('form-'+t).classList.add('active');
}

async function doRegister(){
  const name=gv('r-name'), email=gv('r-email'), dept=gv('r-dept'), password=gv('r-pw');
  const err=document.getElementById('r-err');
  err.className='auth-msg';
  try {
    await api('/register',{method:'POST',body:JSON.stringify({name,email,dept,password})});
    err.className='auth-msg auth-ok'; err.textContent='Account created! Please login.';
    setTimeout(()=>switchAuthTab('login'),1200);
  } catch(e){ err.textContent=e.message; }
}

async function doLogin(){
  const email=gv('l-email'), password=gv('l-pw');
  const err=document.getElementById('l-err');
  try {
    const data = await api('/login',{method:'POST',body:JSON.stringify({email,password})});
    token = data.token;
    localStorage.setItem('ss_token', token);
    currentUser = data.user;
    loadApp();
  } catch(e){ err.textContent=e.message; }
}

function doLogout(){
  token=null; currentUser=null; analysisResult=null; currentApp=null;
  localStorage.removeItem('ss_token');
  document.getElementById('screen-app').classList.remove('active');
  document.getElementById('screen-app').style.display='none';
  document.getElementById('screen-auth').classList.add('active');
  document.getElementById('screen-auth').style.display='flex';
}

async function loadApp(){
  document.getElementById('screen-auth').classList.remove('active');
  document.getElementById('screen-auth').style.display='none';
  document.getElementById('screen-app').classList.add('active');
  document.getElementById('screen-app').style.display='flex';

  const ini=(currentUser.name||'U').split(' ').map(w=>w[0]).join('').toUpperCase().slice(0,2);
  document.getElementById('nav-av').textContent=ini;
  document.getElementById('nav-nm').textContent=currentUser.name.split(' ')[0];
  document.getElementById('s-date').min=new Date().toISOString().split('T')[0];

  // restore theme
  const theme = currentUser.theme || localStorage.getItem('ss_theme') || 'light';
  document.documentElement.setAttribute('data-theme', theme);
  document.getElementById('btn-theme').textContent = theme==='dark'?'☀️':'🌙';

  // load existing application
  try {
    const d = await api('/application');
    if(d.application){
      currentApp = d.application;
      restoreTracker();
    }
  } catch(e){}
  updateProfileTab();
}

// ── THEME ─────────────────────────────────────────────────────────────────────
async function toggleTheme(){
  const isDark = document.documentElement.getAttribute('data-theme')==='dark';
  const next = isDark?'light':'dark';
  document.documentElement.setAttribute('data-theme', next);
  document.getElementById('btn-theme').textContent = isDark?'🌙':'☀️';
  localStorage.setItem('ss_theme', next);
  if(token) api('/theme',{method:'POST',body:JSON.stringify({theme:next})}).catch(()=>{});
}

// ── FILE ──────────────────────────────────────────────────────────────────────
function onFile(input){
  document.getElementById('fname').textContent = input.files[0]?'📎 '+input.files[0].name:'';
}

// ── ANALYSIS ──────────────────────────────────────────────────────────────────
async function runAnalysis(){
  const company=gv('s-company'), role=gv('s-role'), interview_date=gv('s-date');
  const file=document.getElementById('res-file').files[0];
  if(!company||!role){ alert('Please select a company and job role.'); return; }
  if(!interview_date){ alert('Please enter your interview date.'); return; }
  if(!file){ alert('Please upload your resume.'); return; }

  const btn=document.getElementById('btn-go');
  btn.disabled=true;

  try {
    // Upload file
    showLoader('📄 Reading your resume...');
    const formData = new FormData();
    formData.append('resume', file);
    const res = await fetch(API+'/upload-resume',{
      method:'POST', headers:{'Authorization':'Bearer '+token}, body:formData
    });
    const uploadData = await res.json();
    if(!res.ok) throw new Error(uploadData.error);
    const rawText = uploadData.text;

    // Analyze
    showLoader('🧠 Extracting and analyzing skills...');
    const result = await api('/analyze',{method:'POST',body:JSON.stringify({company,role,interview_date,raw_text:rawText})});
    analysisResult = {...result, rawText};

    hideLoader();
    renderResult();

    // Suggest better role
    if(result.best_alt && result.best_alt.missing.length < result.missing.length){
      suggestedRoleData = result.best_alt;
      document.getElementById('m-rs-sub').textContent =
        `For "${result.best_alt.role}" at ${company} you have more skills and need to learn fewer — giving you a better chance!`;
      document.getElementById('m-rs-detail').innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.8rem;font-size:.83rem">
          <div>
            <div style="font-weight:700;color:var(--text3);margin-bottom:.3rem">YOUR ROLE</div>
            <div style="font-weight:700;color:var(--text)">${role}</div>
            <div style="color:var(--red)">${result.missing.length} skills to learn</div>
            <div style="color:var(--blue)">${result.pct}% match</div>
          </div>
          <div>
            <div style="font-weight:700;color:var(--purple);margin-bottom:.3rem">✨ SUGGESTED</div>
            <div style="font-weight:700;color:var(--text)">${result.best_alt.role}</div>
            <div style="color:var(--green)">${result.best_alt.missing.length} skills to learn</div>
            <div style="color:var(--blue)">${result.best_alt.pct}% match</div>
          </div>
        </div>`;
      setTimeout(()=>openM('m-role-sug'), 900);
    }

    btn.textContent='✅ Done!'; btn.style.background='linear-gradient(135deg,var(--green),var(--green-l))';
    setTimeout(()=>{ btn.textContent='🔍 Analyze My Resume'; btn.style.background=''; btn.disabled=false; }, 3000);

  } catch(e){
    hideLoader(); alert('Error: '+e.message);
    btn.textContent='🔍 Analyze My Resume'; btn.disabled=false;
  }
}

function renderResult(){
  const r = analysisResult;
  document.getElementById('res-empty').style.display='none';
  document.getElementById('res-content').style.display='block';
  document.getElementById('rp-title').textContent=`${r.role} @ ${r.company}`;
  document.getElementById('rp-sub').textContent=`${r.matched.length} required skills matched`;
  const el=document.getElementById('rp-elig');
  el.textContent=r.eligible?'✅ Eligible':'❌ Not Eligible';
  el.className='elig '+(r.eligible?'elig-y':'elig-n');
  document.getElementById('rp-pct').textContent=r.pct+'%';
  setTimeout(()=>document.getElementById('rp-bar').style.width=r.pct+'%',100);
  document.getElementById('rp-matched').innerHTML=r.matched.length
    ?r.matched.map(s=>`<span class="pill pm">✓ ${s}</span>`).join('')
    :'<span style="font-size:.78rem;color:var(--text4)">None found</span>';
  document.getElementById('rp-missing').innerHTML=r.missing.length
    ?r.missing.map(s=>`<span class="pill px">✗ ${s}</span>`).join('')
    :'<span style="font-size:.78rem;color:var(--text4)">All matched! 🎉</span>';
  document.getElementById('rp-extra').innerHTML=r.extra.map(s=>`<span class="pill pb">${s}</span>`).join('');
  document.getElementById('rp-extra-w').style.display=r.extra.length?'block':'none';
}

function acceptRoleSuggest(){
  if(!suggestedRoleData||!analysisResult) return;
  analysisResult.role    = suggestedRoleData.role;
  analysisResult.matched = suggestedRoleData.matched;
  analysisResult.missing = suggestedRoleData.missing;
  analysisResult.pct     = suggestedRoleData.pct;
  renderResult();
  closeM('m-role-sug');
}

// ── TRACKER ───────────────────────────────────────────────────────────────────
async function saveToTracker(){
  if(!analysisResult) return;
  const {company,role,interview_date,missing,matched,rawText,pct} = analysisResult;
  const found = analysisResult.extra.concat(matched);
  const today = new Date(), intv = new Date(interview_date);
  const totalDays = Math.max(1, Math.ceil((intv-today)/86400000));
  const per = Math.max(1, Math.floor(totalDays/Math.max(missing.length,1)));
  const skill_items = missing.map((s,i)=>{
    const dl=new Date(today); dl.setDate(dl.getDate()+per*(i+1));
    return{name:s, deadline:dl.toISOString().split('T')[0]};
  });
  try {
    showLoader('💾 Saving your plan...');
    await api('/application',{method:'POST',body:JSON.stringify({
      company,role,interview_date,raw_text:rawText,matched,found,pct,skill_items
    })});
    const d = await api('/application');
    currentApp = d.application;
    hideLoader();
    restoreTracker();
    updateProfileTab();
    showTab('tracker');
  } catch(e){ hideLoader(); alert('Error: '+e.message); }
}

function restoreTracker(){
  if(!currentApp) return;
  document.getElementById('trk-empty').style.display='none';
  document.getElementById('trk-content').style.display='block';
  document.getElementById('trk-title').textContent=`${currentApp.role} @ ${currentApp.company}`;
  document.getElementById('trk-sub').textContent='Interview: '+fmtDate(currentApp.interview_date);
  const dl=Math.ceil((new Date(currentApp.interview_date)-new Date())/86400000);
  const dn=document.getElementById('trk-days');
  dn.textContent=dl>0?dl:'0';
  dn.style.color=dl<=3?'var(--red)':dl<=7?'var(--orange)':'';
  renderChecklist();
  checkSuggestBanner();
}

function renderChecklist(){
  const app=currentApp; if(!app) return;
  const today=new Date();
  const done=app.skill_items.filter(s=>s.done).length;
  const total=app.skill_items.length;
  const pct=total?Math.round(done/total*100):100;
  document.getElementById('st-tot').textContent=total;
  document.getElementById('st-dn').textContent=done;
  document.getElementById('st-lf').textContent=total-done;
  document.getElementById('st-pc').textContent=pct+'%';

  const pb=document.getElementById('prog-bar');
  pb.style.setProperty('--w', pct+'%');
  pb.style.background=`linear-gradient(90deg, var(--blue) ${pct}%, var(--border) ${pct}%)`;

  const bdg=document.getElementById('bdg');
  bdg.textContent=total-done; bdg.style.display=(total-done>0)?'':'none';

  const list=document.getElementById('sk-list');
  if(total===0){
    list.innerHTML='<div style="background:var(--surface2);border-radius:12px;padding:1.4rem;text-align:center;color:var(--text3)">🎉 No missing skills — you matched everything!</div>';
    return;
  }
  list.innerHTML=app.skill_items.map(sk=>{
    const dl=new Date(sk.deadline), dl2=Math.ceil((dl-today)/86400000);
    const urg=!sk.done?(dl2<=2?'urg':dl2<=5?'wrn':''):'';
    return `
    <div class="sk-item${sk.done?' done':''}" id="ski-${sk.id}">
      <div class="sk-top">
        <div class="sk-check">${sk.done?'✓':''}</div>
        <div style="flex:1">
          <div class="sk-name">${sk.name}</div>
          <div class="sk-dl ${urg}">📅 Learn by ${fmtDate(sk.deadline)} ${!sk.done?(dl2>0?`· ${dl2} days left`:'· ⚠️ Overdue!'):'· ✅ Completed'}</div>
        </div>
      </div>
      ${!sk.done?`<div class="sk-actions">
        <button class="btn-vid" onclick="toggleVids(${sk.id})">▶️ Watch Videos</button>
        <button class="btn-qz" onclick="startQuiz('${sk.name.replace(/'/g,"\\'")}',${sk.id})">📝 Take Quiz to Complete</button>
      </div>`:''}
      <div class="vid-panel" id="vp-${sk.id}"></div>
    </div>`;
  }).join('');
  if(pct===100&&total>0) setTimeout(()=>openM('m-congrats'),700);
}

async function toggleVids(skillId){
  const panel=document.getElementById('vp-'+skillId);
  if(panel.style.display==='block'){ panel.style.display='none'; return; }
  const sk=currentApp.skill_items.find(s=>s.id===skillId);
  if(!sk) return;
  if(!panel.innerHTML){
    try {
      const d=await api('/videos/'+encodeURIComponent(sk.name));
      panel.innerHTML=d.videos.map(v=>`
        <div class="vid-row">
          <a class="vid-thumb" href="${v.u}" target="_blank">▶️</a>
          <div class="vid-info"><div class="vid-title">${v.t}</div><div class="vid-ch">📺 ${v.ch}</div></div>
          <a class="vid-link" href="${v.u}" target="_blank">Watch →</a>
        </div>`).join('');
    } catch(e){ panel.innerHTML='<div style="font-size:.82rem;color:var(--text3)">No videos found.</div>'; }
  }
  panel.style.display='block';
}

// ── QUIZ ──────────────────────────────────────────────────────────────────────
let QS = null;

async function startQuiz(skillName, skillId){
  try {
    showLoader('Loading quiz questions...');
    const d = await api('/quiz/'+encodeURIComponent(skillName));
    hideLoader();
    QS = {skillName, skillId, questions:d.questions, current:0, score:0};
    renderQuiz();
    openM('m-quiz');
  } catch(e){ hideLoader(); alert('Error loading quiz: '+e.message); }
}

function renderQuiz(){
  const inner=document.getElementById('quiz-inner');
  if(QS.current>=QS.questions.length){
    const pass=QS.score>=QS.questions.length;
    inner.innerHTML=`
      <div class="qz-score">
        <div style="font-size:2.8rem;margin-bottom:.5rem">${pass?'🎉':'😔'}</div>
        <div style="font-family:var(--fd);font-weight:800;font-size:1.3rem;margin-bottom:.4rem;color:var(--text)">${pass?'Perfect Score!':'Quiz Failed'}</div>
        <div class="qs-big">${QS.score}/${QS.questions.length}</div>
        <div style="font-size:.8rem;color:var(--text3);margin:.3rem 0 .7rem">Correct Answers</div>
        <div style="font-size:.92rem;font-weight:600;color:${pass?'var(--green)':'var(--red)'};margin-bottom:1.2rem">
          ${pass?`✅ "${QS.skillName}" has been marked as completed!`:`❌ You need all ${QS.questions.length}/3 correct. Try again with new questions!`}
        </div>
        <div style="display:flex;gap:.7rem;justify-content:center;flex-wrap:wrap">
          <button class="btn-no" onclick="closeM('m-quiz')">${pass?'Close':'Close & Study More'}</button>
          ${!pass?`<button class="btn-yes" onclick="retryQuiz()">🔄 Try Again (New Questions)</button>`:''}
        </div>
      </div>`;
    if(pass) completeSkillInDB();
    return;
  }
  const q=QS.questions[QS.current];
  inner.innerHTML=`
    <div>
      <div class="qz-skill">📝 Quiz: ${QS.skillName}</div>
      <div class="qz-prog-bar"><div class="qz-prog-fill" style="width:${QS.current/QS.questions.length*100}%"></div></div>
      <div class="qz-meta"><span>Question ${QS.current+1} of ${QS.questions.length}</span><span>Score: ${QS.score}</span></div>
      <div class="qz-q">${q.q}</div>
      <div class="qz-opts">${q.o.map((opt,i)=>`<button class="qz-opt" onclick="answer(${i})">${opt}</button>`).join('')}</div>
      <div class="qz-fb" id="qz-fb"></div>
    </div>`;
}

function answer(chosen){
  const q=QS.questions[QS.current];
  document.querySelectorAll('.qz-opt').forEach(o=>o.disabled=true);
  const fb=document.getElementById('qz-fb'); fb.style.display='block';
  if(chosen===q.a){
    document.querySelectorAll('.qz-opt')[chosen].classList.add('correct');
    fb.className='qz-fb ok'; fb.textContent='✅ Correct! Well done.';
    QS.score++;
  } else {
    document.querySelectorAll('.qz-opt')[chosen].classList.add('wrong');
    document.querySelectorAll('.qz-opt')[q.a].classList.add('reveal');
    fb.className='qz-fb bad'; fb.textContent=`❌ Wrong! Correct: "${q.o[q.a]}"`;
  }
  setTimeout(()=>{ QS.current++; renderQuiz(); }, 1500);
}

async function completeSkillInDB(){
  try {
    await api(`/skill/${QS.skillId}/complete`,{method:'POST'});
    // update local state
    const sk=currentApp.skill_items.find(s=>s.id===QS.skillId);
    if(sk) sk.done=true;
    renderChecklist(); updateProfileTab(); updateResumeDisplay();
  } catch(e){ console.error(e); }
}

async function retryQuiz(){
  try {
    showLoader('Getting new questions...');
    const d=await api('/quiz/'+encodeURIComponent(QS.skillName));
    hideLoader();
    QS.questions=d.questions; QS.current=0; QS.score=0;
    renderQuiz();
  } catch(e){ hideLoader(); alert('Error: '+e.message); }
}

// ── SUGGEST BANNER ────────────────────────────────────────────────────────────
function checkSuggestBanner(){
  const app=currentApp; if(!app) return;
  const dl=Math.ceil((new Date(app.interview_date)-new Date())/86400000);
  const rem=app.skill_items.filter(s=>!s.done);
  const banner=document.getElementById('sug-banner');
  if(dl<=7&&rem.length>2){
    const found=new Set([...app.matched,...app.skill_items.filter(s=>s.done).map(s=>s.name)]);
    const ROLE_SKILLS_FE={
      'Software Developer':['python','java','javascript','sql','git','rest api','linux','oop','data structures','algorithms','html','css'],
      'Data Scientist':['python','r','machine learning','tensorflow','pandas','numpy','sql','statistics','data visualization','scikit-learn','deep learning'],
      'Machine Learning Engineer':['python','tensorflow','pytorch','scikit-learn','deep learning','nlp','docker','kubernetes','mlops','sql','algorithms'],
      'Full Stack Developer':['html','css','javascript','react','node.js','mongodb','sql','git','rest api','typescript','docker','express'],
      'DevOps Engineer':['linux','docker','kubernetes','jenkins','aws','ci/cd','terraform','ansible','bash','python','monitoring','git'],
      'Business Analyst':['sql','excel','power bi','tableau','agile','scrum','requirements gathering','data analysis','communication','jira','statistics'],
      'Cloud Architect':['aws','azure','gcp','kubernetes','docker','terraform','networking','security','microservices','python','iam','devops'],
    };
    const alts=Object.entries(ROLE_SKILLS_FE)
      .filter(([r])=>r!==app.role)
      .map(([r,sk])=>({role:r, extra:sk.filter(s=>!found.has(s)).length, matched:sk.filter(s=>found.has(s)), skills:sk}))
      .sort((a,b)=>a.extra-b.extra);
    if(!alts.length) return;
    suggestedRoleData=alts[0];
    document.getElementById('sug-text').innerHTML=
      `You have <strong>${rem.length} skills</strong> remaining with only <strong>${dl} day${dl!==1?'s':''}</strong> until your interview for "<strong>${app.role}</strong>". The role "<strong>${alts[0].role}</strong>" requires only <strong>${alts[0].extra}</strong> more skill(s) from your current profile. Switch?`;
    banner.style.display='block';
  } else { banner.style.display='none'; }
}

async function acceptSuggest(){
  if(!suggestedRoleData||!currentApp) return;
  const today=new Date(), idate=new Date(currentApp.interview_date);
  const totalDays=Math.max(1,Math.ceil((idate-today)/86400000));
  const found=new Set([...currentApp.matched,...currentApp.skill_items.filter(s=>s.done).map(s=>s.name)]);
  const ROLE_SKILLS_FE={
    'Software Developer':['python','java','javascript','sql','git','rest api','linux','oop','data structures','algorithms','html','css'],
    'Data Scientist':['python','r','machine learning','tensorflow','pandas','numpy','sql','statistics','data visualization','scikit-learn','deep learning'],
    'Machine Learning Engineer':['python','tensorflow','pytorch','scikit-learn','deep learning','nlp','docker','kubernetes','mlops','sql','algorithms'],
    'Full Stack Developer':['html','css','javascript','react','node.js','mongodb','sql','git','rest api','typescript','docker','express'],
    'DevOps Engineer':['linux','docker','kubernetes','jenkins','aws','ci/cd','terraform','ansible','bash','python','monitoring','git'],
    'Business Analyst':['sql','excel','power bi','tableau','agile','scrum','requirements gathering','data analysis','communication','jira','statistics'],
    'Cloud Architect':['aws','azure','gcp','kubernetes','docker','terraform','networking','security','microservices','python','iam','devops'],
  };
  const newRole=suggestedRoleData.role;
  const newMissing=(ROLE_SKILLS_FE[newRole]||[]).filter(s=>!found.has(s));
  const newMatched=(ROLE_SKILLS_FE[newRole]||[]).filter(s=>found.has(s));
  const per=Math.max(1,Math.floor(totalDays/Math.max(newMissing.length,1)));
  const skill_items=newMissing.map((s,i)=>{
    const dl=new Date(today); dl.setDate(dl.getDate()+per*(i+1));
    return{name:s, deadline:dl.toISOString().split('T')[0]};
  });
  try {
    showLoader('Switching role...');
    await api('/application/switch-role',{method:'POST',body:JSON.stringify({role:newRole, matched:newMatched, skill_items})});
    const d=await api('/application');
    currentApp=d.application;
    hideLoader();
    document.getElementById('sug-banner').style.display='none';
    restoreTracker(); updateProfileTab();
    alert(`✅ Switched to "${newRole}"! Tracker updated.`);
  } catch(e){ hideLoader(); alert('Error: '+e.message); }
}

// ── PROFILE & RESUME ──────────────────────────────────────────────────────────
function updateProfileTab(){
  if(!currentUser) return;
  const ini=(currentUser.name||'U').split(' ').map(w=>w[0]).join('').toUpperCase().slice(0,2);
  document.getElementById('pr-av').textContent=ini;
  document.getElementById('pr-nm').textContent=currentUser.name;
  document.getElementById('pr-dept').textContent=currentUser.dept||'—';
  document.getElementById('pr-em').textContent=currentUser.email;
  if(currentApp){
    const a=currentApp;
    document.getElementById('pr-role').textContent=`${a.role} @ ${a.company}`;
    document.getElementById('pr-co').textContent=a.company;
    document.getElementById('pr-dt').textContent=fmtDate(a.interview_date);
    document.getElementById('pr-mt').textContent=(a.pct||'—')+'%';
    const done=a.skill_items.filter(s=>s.done).length;
    document.getElementById('pr-lrn').textContent=`${done} / ${a.skill_items.length}`;
  } else {
    ['pr-role','pr-co','pr-dt','pr-mt','pr-lrn'].forEach(id=>document.getElementById(id).textContent='—');
    document.getElementById('pr-role').textContent='No active application';
  }
  updateResumeDisplay();
}

function updateResumeDisplay(){
  const app=currentApp;
  const disp=document.getElementById('res-display');
  if(!app){ disp.innerHTML='<div class="no-app-box">No resume yet. <a onclick="showTab(\'analyze\')" style="cursor:pointer">Analyze first →</a></div>'; return; }
  const learned=app.skill_items.filter(s=>s.done).map(s=>s.name);
  const missing=app.skill_items.filter(s=>!s.done).map(s=>s.name);
  const allSkills=[...new Set([...app.matched,...learned])];
  const allDone=missing.length===0&&app.skill_items.length>0;
  let resumeText = buildResumeText(app, allSkills, missing);
  disp.innerHTML=`
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.7rem;margin-bottom:.9rem">
      <div style="font-size:.8rem;color:${allDone?'var(--green)':'var(--text3)'};font-weight:${allDone?700:400}">
        ${allDone?'✅ All skills mastered — resume fully updated!':'Updated with skills completed so far.'}
      </div>
      <button class="btn-dl" onclick="downloadResume()">⬇️ Download Resume</button>
    </div>
    <div class="resume-box">${escH(resumeText)}</div>`;
}

function buildResumeText(app, allSkills, stillMissing){
  const u=currentUser;
  const updatedSection =
    '\n\n────────────────────────────────\n'+
    'SKILLS — Updated by SkillSync AI ('+new Date().toLocaleDateString('en-IN')+')\n'+
    '────────────────────────────────\n'+
    allSkills.join(', ') +
    (stillMissing.length ? '\n\nIN PROGRESS: '+stillMissing.join(', ') : '');
  if(app.raw_text) return app.raw_text.trim() + updatedSection;
  return [
    u.name.toUpperCase(), u.email+' | '+u.dept,'',
    'TARGET: '+app.role+' @ '+app.company,
    'INTERVIEW: '+fmtDate(app.interview_date),'',
    '════════════════════════',
    'VERIFIED SKILLS','════════════════════════',
    allSkills.join(', ')||'None yet',
    stillMissing.length?'\nIN PROGRESS:\n'+stillMissing.join(', '):'',
  ].join('\n');
}

function downloadResume(){
  const app=currentApp; if(!app){ alert('No resume to download.'); return; }
  const learned=app.skill_items.filter(s=>s.done).map(s=>s.name);
  const missing=app.skill_items.filter(s=>!s.done).map(s=>s.name);
  const allSkills=[...new Set([...app.matched,...learned])];
  const content=buildResumeText(app, allSkills, missing);
  const blob=new Blob([content],{type:'text/plain'});
  const url=URL.createObjectURL(blob);
  const a=document.createElement('a');
  a.href=url; a.download=`Resume_${currentUser.name.replace(/\s+/g,'_')}_Updated.txt`;
  a.click(); URL.revokeObjectURL(url);
}

// ── UI HELPERS ────────────────────────────────────────────────────────────────
function showTab(t){
  document.querySelectorAll('.app-tab').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
  document.getElementById('tab-'+t).classList.add('active');
  document.getElementById('panel-'+t).classList.add('active');
  if(t==='profile') updateProfileTab();
  if(t==='tracker') checkSuggestBanner();
}
const openM = id => document.getElementById(id).classList.add('active');
const closeM = id => document.getElementById(id).classList.remove('active');
const fmtDate = d => d ? new Date(d+'T00:00:00').toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'}) : '—';
const gv = id => document.getElementById(id).value.trim();
const escH = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

// ── INIT ──────────────────────────────────────────────────────────────────────
(async function init(){
  const savedTheme=localStorage.getItem('ss_theme')||'light';
  document.documentElement.setAttribute('data-theme',savedTheme);
  if(token){
    try {
      currentUser = await api('/me');
      await loadApp();
      return;
    } catch(e){ token=null; localStorage.removeItem('ss_token'); }
  }
  document.getElementById('screen-auth').style.display='flex';
})();
