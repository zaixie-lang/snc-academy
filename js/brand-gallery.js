/* Shared still-image gallery and brand detail controller. */
(()=>{
 const el=(tag,text)=>{const e=document.createElement(tag);if(text)e.textContent=text;return e};
 const validFile=s=>typeof s==='string'&&/^[\w.-]+\.(webp|jpe?g|png|avif)$/i.test(s);
 const validId=s=>typeof s==='string'&&/^[\w-]{11}$/.test(s);
 const thumb=id=>'https://i.ytimg.com/vi/'+id+'/hqdefault.jpg';
 const mq=matchMedia('(max-width:767px)');
 const viewer=el('dialog');viewer.className='brand-photo-viewer';viewer.setAttribute('aria-label','갤러리 사진 확대');
 const close=el('button','닫기 ×'),full=el('img');close.type='button';viewer.append(close,full);document.body.append(viewer);
 close.onclick=()=>viewer.close();viewer.addEventListener('click',e=>{if(e.target===viewer)viewer.close()});viewer.addEventListener('close',()=>full.removeAttribute('src'));
 function scroll(target){const h=document.getElementById('header');window.scrollTo({top:Math.max(0,target.getBoundingClientRect().top+scrollY-(h?h.getBoundingClientRect().bottom:0)-12),behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'})}
 function arrange(g){
  const fs=[...g.children].filter(f=>f.tagName==='FIGURE'),ps=fs.filter(f=>f.classList.contains('is-portrait'));
  const n=fs.length,k=ps.length;
  g.dataset.layout=n===2&&k===0?'a':n===2&&k===2?'b':n===3&&k===1?'c':n===4&&k===0?'d':'fallback';
  fs.forEach(f=>f.style.removeProperty('--gallery-row'));
  if(g.dataset.layout==='c')fs.filter(f=>!f.classList.contains('is-portrait')).forEach((f,i)=>f.style.setProperty('--gallery-row',i+1));
 }
 function card(r,url,title,image,label){const a=el('a');a.href=url;a.target='_blank';a.rel='noopener noreferrer';if(image){const im=el('img');im.alt='';im.loading='eager';im.decoding='async';im.onerror=()=>im.remove();im.src=image;a.append(im)}if(label)a.append(el('span',label));a.append(el('strong',title));r.append(a)}
 for(const p of document.querySelectorAll('.brand-inline[data-brand]')){
  const slug=p.dataset.brand;if(!/^[a-z0-9-]+$/.test(slug))continue;
  const t=document.querySelector('[aria-controls="'+p.id+'"]'),g=p.querySelector('.brand-gallery'),r=p.querySelector('.brand-related');if(!t||!g||!r)continue;
  const owner=t.closest('.program-card'),marker=document.createComment('desktop brand position');p.before(marker);
  function place(){if(mq.matches)owner.after(p);else marker.after(p)}place();mq.addEventListener('change',place);
  const base='images/brands/'+slug+'/gallery/';let loaded=false;
  async function load(){if(loaded)return;loaded=true;try{
   const response=await fetch('data/'+slug+'.json',{cache:'no-store'});if(!response.ok)throw Error();const c=await response.json();g.replaceChildren();r.replaceChildren();
   for(const item of (c.gallery||[]).filter(x=>x.type==='image'&&validFile(x.file)).slice(0,4)){
    const f=el('figure'),a=el('a'),im=el('img'),cap=el('figcaption',item.title||'');a.href=base+item.file;a.target='_blank';a.rel='noopener noreferrer';a.setAttribute('aria-label',(item.title||'사진')+' 확대 보기');im.alt=item.title||'';im.loading='eager';im.decoding='async';
    const orient=()=>{if(!im.naturalWidth)return;f.classList.toggle('is-portrait',im.naturalHeight>im.naturalWidth);arrange(g)};im.addEventListener('load',orient);im.addEventListener('error',()=>{f.remove();arrange(g)});a.append(im);f.append(a,cap);g.append(f);im.src=a.href;if(im.complete)orient();
    a.addEventListener('click',e=>{if(typeof viewer.showModal!=='function'||e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();full.src=a.href;full.alt=im.alt;viewer.showModal()});
   }arrange(g);
   if(p.hasAttribute('data-content-layout')){
    const gallerySection=g.closest('section');const syncGallery=()=>{gallerySection.hidden=!g.querySelector('figure')};syncGallery();new MutationObserver(syncGallery).observe(g,{childList:true});
    const safe=(v,hosts)=>{try{const u=new URL(v);return u.protocol==='https:'&&hosts.includes(u.hostname)?u:null}catch{return null}};
    const ytHosts=['www.youtube.com','youtube.com','m.youtube.com','youtu.be'];
    const v=safe(c.video?.url,ytHosts);let id=v&&(v.hostname==='youtu.be'?v.pathname.slice(1):v.pathname.startsWith('/shorts/')?v.pathname.split('/')[2]:v.searchParams.get('v'));
    const blogs=el('div');blogs.className='managed-blog-grid';
    let posts=[];try{const res=await fetch('data/blog-posts.json',{cache:'no-store'});posts=(await res.json()).posts||[]}catch{}
    for(const [i,b] of (Array.isArray(c.blogs)?c.blogs:[]).slice(0,2).entries()){
     const u=safe(b.url,['blog.naver.com','m.blog.naver.com']);if(!u)continue;
     const post=posts.find(x=>x.url&&x.url.split('?')[0].replace(/\/$/,'').endsWith(u.pathname.replace(/\/$/,'')));
     card(blogs,u.href,b.title||post?.title||'관련 교육 이야기 '+(i+1),b.image||post?.image,'관련 블로그 ↗');
    }
    r.classList.toggle('has-video',!!validId(id));
    if(validId(id)){const video=el('div');video.className='managed-video';card(video,v.href,c.video.title||'대표 영상',thumb(id),'▶ 유튜브 영상 보기 ↗');r.append(video)}
    if(blogs.children.length){if(blogs.children.length===1)blogs.style.gridTemplateColumns='1fr';r.append(blogs);}
    const channel=safe(c.channel?.url,ytHosts);const nav=p.querySelector('.managed-channel');if(nav){nav.replaceChildren();if(channel)card(nav,channel.href,c.channel.title||'유튜브 채널',null,'▶');nav.hidden=!channel}
    r.hidden=!r.children.length;return;
   }
   if(c.youtube&&validId(c.youtube.id))card(r,'https://www.youtube.com/watch?v='+c.youtube.id,c.youtube.title||'관련 영상',thumb(c.youtube.id),'유튜브 영상 보기 ↗');
   if(c.clip&&typeof c.clip.url==='string'&&c.clip.url.startsWith('https://clip.naver.com/'))card(r,c.clip.url,c.clip.title,c.clip.image,'');
   if(c.blog&&/^\d+$/.test(c.blog.id)){let image=c.blog.image||'';try{const res=await fetch('data/blog-posts.json',{cache:'no-store'});const d=await res.json();const post=(d.posts||[]).find(x=>x.url&&x.url.endsWith('/'+c.blog.id));if(post&&post.image)image=post.image}catch{}card(r,'https://blog.naver.com/hannak74/'+c.blog.id,c.blog.title,image,'관련 블로그 살펴보기 ↗')}
  }catch{loaded=false;g.textContent='갤러리를 불러오지 못했습니다.'}}
  t.addEventListener('click',e=>{e.preventDefault();e.stopImmediatePropagation();const opening=p.hidden;document.querySelectorAll('.program-expand').forEach(b=>{b.setAttribute('aria-expanded','false');const x=document.getElementById(b.getAttribute('aria-controls'));if(x)x.hidden=true});if(opening){p.querySelectorAll('img[data-src]').forEach(im=>{im.src=im.dataset.src;im.removeAttribute('data-src')});p.hidden=false;t.setAttribute('aria-expanded','true');load();requestAnimationFrame(()=>requestAnimationFrame(()=>{if(!p.hidden)scroll(p)}))}else requestAnimationFrame(()=>scroll(owner))},true);
  p.querySelector('.brand-close').onclick=()=>{t.click();t.focus({preventScroll:true})};new MutationObserver(()=>{if(p.hidden&&viewer.open)viewer.close()}).observe(p,{attributes:true,attributeFilter:['hidden']});
 }
})();
