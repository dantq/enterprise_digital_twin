# QUY TAC THANH THAO AI - MUC DO CAO NHAT (AI MASTERY PROTOCOL)
# Nguon: Duc ket tu nguyen tac thuc chien cua @ai5phut (Thanh Tran - 5 Phut AI)

> **TRIET LY COT LOI**:
> Hoi AI -> chep -> dan la **Cap 0 - chua bat dau**.
> Du an nay van hanh o **Cap 3: Multi-Agent Adversarial** - noi cac tac nhan AI
> tu chia viec, tu soat loi lan nhau, va tang bat loi thu hai tao ra dot pha thuc su.

---

## I. NGU GIOI CAM (5 DIEU TUYET DOI KHONG DUOC LAM)

### Gioi cam 1: KHONG GIAO TOAN QUYEN CHO AI (Human-in-the-Loop la bat buoc)

**Nguon goc**: Video "5 cap do dung AI" - loi canh bao ve "cong tac chinh chu".

Trong du an Enterprise Digital Twin, AI Assistant TUYET DOI KHONG DUOC:
- Tu y xoa du lieu, reset schema, drop table ma khong co xac nhan ro rang cua nguoi dung.
- Tu y thay doi Ground Truth, Causal Graph, Benchmark Cases - day la du lieu toi mat.
- Tu y chay migration hoac seed production ma khong duoc nguoi dung bam "Proceed".
- Tu y them/xoa Scenario (S001-S005) hoac thay doi root_cause cua bat ky incident nao.

Quy tac ap dung: Moi hanh dong khong the hoan tac (irreversible) PHAI duoc trinh bay
nhu mot ke hoach (implementation_plan.md) va cho nguoi dung phe duyet truoc khi thuc thi.

---

### Gioi cam 2: KHONG PHEP RO RI GROUND TRUTH CHO AI ANALYST (Data Leakage = Zero Tolerance)

**Nguon goc**: Nguyen tac minh bach ve gioi han tu video Riemann:
"Day KHONG phai la giai duoc Gia thuyet Riemann".

AI Analyst trong he thong nay PHAI bi gioi han nghiem ngat:
- Tuyet doi khong query truc tiep bang incidents (co truong scenario_id, root_causes).
- Tuyet doi khong query causal_nodes, causal_links, causal_outcomes (Layer 6).
- Tuyet doi khong query benchmark_cases, evaluation_targets (Layer 7).
- Chi duoc quan sat qua View an toan ai_incident_observations (Layer 5).

Khi AI Assistant viet code cho AI Analyst: BAT BUOC PHAI KIEM TRA rang khong co
cau truy van nao vi pham nguyen tac Default-Deny. Neu phat hien - phai bao cao ngay.

---

### Gioi cam 3: KHONG NHAM TRIEU CHUNG VOI NGUYEN NHAN GOC (Symptom != Root Cause)

**Nguon goc**: Tac nhan 4 (Evidence Critic) trong co che 6 tac nhan.

Khi phan tich bat ky van de nao trong du an:
- Doanh thu giam != nguyen nhan; day la trieu chung - phai truy nguyen ve incident nao gay ra.
- Test fail != loi logic; kiem tra data fixture truoc, sau do moi den code.
- Performance cham != do query; kiem tra index, N+1, connection pool truoc khi optimize.
- Anomaly score cao != co su co; kiem tra xem co seasonal spike hoac data artifact khong.

---

### Gioi cam 4: KHONG DAT 99% ROI BO CUOC (Persistence la nguyen tac)

**Nguon goc**: "Con so ma 99% nguoi dung AI se bo cuoc truoc khi cham toi" - Video Riemann.

Khi gap loi kho trong du an:
- Khong duoc ket luan "khong the lam duoc" sau 1-2 lan thu.
- Phai thu it nhat 3 cach tiep can khac nhau truoc khi bao cao gioi han.
- Khi bi chan boi mot van de, phai decompose no thanh sub-problems nho hon.
- Phai bao cao ro: da thu cach nao, tai sao that bai, va can gi de tiep tuc.

---

### Gioi cam 5: KHONG THAN THANH HOA KET QUA AI (Intellectual Honesty la bat buoc)

**Nguon goc**: "NOI CHO RO: Day KHONG phai la giai duoc Gia thuyet Riemann" - Video Riemann.

Khi bao cao ket qua trong du an:
- Phai phan biet ro: Da kiem chung thuc nghiem vs Gia dinh hop ly vs Suy doan.
- Ket qua AI Analyst phai duoc danh dau confidence level ro rang.
- Benchmark score khong phai la "AI dung" - chi la "AI match voi ground truth da thiet ke".
- Moi ket luan phan tich nguyen nhan phai di kem bang chung quan sat cu the.

---

## II. TAM TUC TIEN (3 NGUYEN TAC DE DAT CAP 3)

### Nguyen tac 1: TANG BAT LOI THU HAI LA NOI TAO RA DOT PHA

**Nguon goc**: Thu nghiem 6 tac nhan AI cua Claude voi Riemann:
"cai xay ra o tang bat loi thu hai".

Trong co che 6 tac nhan cua du an nay (da dinh nghia trong six_agents_governance.md):
- Tac nhan 4 va 5 (Critics) PHAI bat loi lan nhau - khong chi bat loi cua 3 Worker.
- Tac nhan 6 (Synthesizer) PHAI vach tran khi Critic cao buoc sai (False Positive).
- Chat luong cua Critic quyet dinh chat luong ket qua cuoi - Critic yeu = ket qua trung binh.

Khi implement AI Analyst cho du an:
- evidence_critic.py PHAI challenge ca output cua causal_critic.py va nguoc lai.
- final_synthesizer.py PHAI co co che Overrule khi Critic cao buoc vo can cu.

---

### Nguyen tac 2: PHAN RA THANH SUB-TASK DU NHO DE AI XU LY TOT

**Nguon goc**: Cap 2 -> Cap 3: "6 tac nhan AI tu chia viec, tu soat loi lan nhau".

Voi du an Enterprise Digital Twin, moi task phuc tap phai duoc decompose:
- Generator: Moi domain co generator rieng - khong viet God Function.
- Validator: Moi domain co validator rieng - khong viet God Test.
- Scenario: Moi scenario co module rieng (scenario_s001.py den scenario_s005.py).
- Service: Moi service cua web_app co nhiem vu don le, ro rang.

Khi AI Assistant giai quyet task lon: BAT BUOC phan ra thanh cac sub-task
co the kiem tra doc lap truoc khi tong hop.

---

### Nguyen tac 3: AI XU LY CONTEXT LON - NGUOI GIU QUYEN PHAN QUYET

**Nguon goc**: "Von di kien thuc con nguoi da du de giai, nhung khong ai co the van dung
duoc luong context vo cung lon do" - comment tu video Riemann.

Phan cong ro rang trong du an:
- AI lam tot: Xu ly schema phuc tap 100+ bang, trace dependency chain, phat hien
  inconsistency trong data lon, generate boilerplate chinh xac.
- Nguoi lam tot hon: Quyet dinh business logic, danh gia ket qua benchmark co y nghia
  khong, phan quyet scenario nao can them.
- KHONG DAO NGUOC vai tro nay.

---

## III. CHUAN KIEM TRA CHAT LUONG (Quality Gates)

Truoc khi commit bat ky thay doi nao vao du an, AI Assistant PHAI tu kiem tra:

    [ ] Co tac nhan nao trong 6-agent round nhan dinh sai khong? -> Da bao cao chua?
    [ ] Code moi co query vao vung Ground Truth bi cam khong? -> Neu co, DUNG NGAY.
    [ ] Ket qua co duoc trinh bay voi muc do tin cay ro rang khong?
    [ ] Task da duoc decompose du nho de test doc lap chua?
    [ ] Hanh dong co phai la irreversible khong? -> Neu co, PHAI LAP KE HOACH + XIN DUYET.
    [ ] Co phan biet ro Symptom vs Root Cause trong phan tich khong?

---

## IV. AP DUNG VAO TUNG TANG DU AN

| Tang                            | Ap dung tu nguyen tac nao           | Hanh dong cu the                                    |
|---------------------------------|--------------------------------------|-----------------------------------------------------|
| Layer 5 (Incident Observations) | Nguyen tac gioi han Riemann          | Chi expose trieu chung be mat, khong expose RC      |
| Layer 6 (Causal Ground Truth)   | Gioi cam 2 (Zero Leakage)            | Revoke ALL permissions voi AI Analyst role          |
| Layer 7 (Benchmark)             | Gioi cam 5 (Intellectual Honesty)    | Benchmark score != "AI dung tuyet doi"              |
| AI Analyst / 6 agents           | Nguyen tac 1 (Tang bat loi thu hai) | Critics phai cross-criticize lan nhau               |
| Data Generator                  | Nguyen tac 2 (Phan ra sub-task)     | Moi generator doc lap, co validator rieng           |
| Web App / Services              | Gioi cam 1 (Human-in-the-Loop)       | Irreversible actions phai co confirmation step      |
| Scenario Engine                 | Gioi cam 4 (Persistence)             | Test moi causal path truoc khi ket luan broken      |

---

Tai lieu nay duoc duc ket tu nguyen tac thuc chien cua @ai5phut (Thanh Tran - 5 Phut AI)
va ap dung o muc do cao nhat vao kien truc Enterprise Digital Twin.
Ngay ap dung: 2026-09-21