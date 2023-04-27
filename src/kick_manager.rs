use serenity::prelude::Context;
use tokio::task::JoinHandle;

pub struct KickManager {
    running_kicks: Vec<(i64, JoinHandle<anyhow::Result<()>>)>,
    context: Option<Context>,
}

impl KickManager {
    pub fn new() -> Self {
        Self {
            running_kicks: vec![],
            context: None,
        }
    }

    pub fn provide_context(&mut self, ctx: Context) {
        // Replace the current context, or lack thereof, with the provided context -- is this a good idea?
        self.context = Some(ctx);
    }

    pub async fn submit_kick(&mut self, kick_id: i64) {
        // Make sure that we hold a Context.
        if self.context.is_none() {
            panic!("Tried to submit_kick without a Context!");
        }
        let ctx = self.context.clone().unwrap();

        // First remove all the running kicks that have concluded.
        self.remove_done_kicks();
        // Now check if there is a kick with this ID
        if self.running_kicks.iter().find(|i| i.0 == kick_id).is_some() {
            // If there is, ignore this submission
            return;
        }

        // If there isn't, now we can add the pending kick to the running kicks.
        self.running_kicks.push((
            kick_id,
            tokio::spawn(crate::perform_kick::run_kick(ctx, kick_id)),
        ));
    }

    fn remove_done_kicks(&mut self) {
        // TODO: when the kick returns an error, should we retry the kick?
        self.running_kicks.retain(|i| !i.1.is_finished());
    }
}
