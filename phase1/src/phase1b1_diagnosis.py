import pandas as pd,numpy as np,matplotlib.pyplot as plt
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'phase1/results/phase1b1_diagnosis';x=pd.read_parquet(R/'phase1/results/phase1b_segmentation/predictions/heldout_transition_predictions.parquet');f=pd.read_csv(R/'phase1/results/phase1b_segmentation/feature_statistics.csv')
rows=[]
for t in np.arange(.1,1,.1):
 p=x.score>=t;tp=(p&(x.y==1)).sum();fp=(p&(x.y==0)).sum();fn=((~p)&(x.y==1)).sum();pr=tp/(tp+fp) if tp+fp else 0;re=tp/(tp+fn) if tp+fn else 0;rows.append({'threshold':t,'precision':pr,'recall':re,'f1':2*pr*re/(pr+re) if pr+re else 0,'predicted_boundary_count':p.sum(),'true_boundary_count':int(x.y.sum())})
pd.DataFrame(rows).to_csv(O/'threshold_results.csv',index=False);f.assign(abs_coefficient=f.coefficient.abs()).sort_values('abs_coefficient',ascending=False).to_csv(O/'feature_analysis.csv',index=False)
cols=['session_id','timestamp_iso','score','gap','active_app','event_type','execution_id','y','pred'];x[(x.y==0)&(x.score>=.8)][cols].head(100).to_csv(O/'false_positive_examples.csv',index=False);x[(x.y==1)&(x.score<=.2)][cols].head(100).to_csv(O/'false_negative_examples.csv',index=False)
fig,ax=plt.subplots(figsize=(8,5));ax.hist(x[x.y==1].score,bins=40,alpha=.6,label='True boundaries');ax.hist(x[x.y==0].score,bins=40,alpha=.6,label='Non-boundaries');ax.legend();ax.set_title('Held-out probability overlap');ax.set_xlabel('Predicted boundary probability');fig.tight_layout();fig.savefig(O/'plots/probability_overlap.png',dpi=160);plt.close(fig)
fig,ax=plt.subplots(figsize=(7,5));d=pd.DataFrame(rows);ax.plot(d.threshold,d.precision,label='precision');ax.plot(d.threshold,d.recall,label='recall');ax.plot(d.threshold,d.f1,label='F1');ax.legend();ax.set_title('Threshold diagnosis');fig.tight_layout();fig.savefig(O/'plots/threshold_metrics.png',dpi=160);plt.close(fig)
print({'positive':int(x.y.sum()),'negative':int((x.y==0).sum()),'positive_rate':float(x.y.mean()),'boundary_score_median':float(x[x.y==1].score.median()),'nonboundary_score_median':float(x[x.y==0].score.median())})
