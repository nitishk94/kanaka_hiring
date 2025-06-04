from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from myapp.auth.decorators import role_required, no_cache
from myapp.models.interviews import Interview
from myapp.models.applicants import Applicant
from myapp.models.referrals import Referral
from myapp.models.users import User
from myapp.models.jobrequirement import JobRequirement
from myapp.extensions import db
from sqlalchemy.orm import joinedload

bp = Blueprint('jobs', __name__, url_prefix='/jobs')
HR_ROLES = ('hr', 'admin')

@bp.route('/view_joblisting')
@no_cache
@login_required
def view_joblisting():
    job_listings = JobRequirement.query.all()
    return render_template('hr/view_applicant.html', job_listings=job_listings)


@bp.route('/uploadjoblistings', methods=['GET', 'POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def upload_joblistings():
    if '_user_id' not in session:
        current_app.logger.warning(f"Session expired for user {current_user.username}")
        return {'error': 'Session expired. Please log in again.'}, 401
        
        # Get all form data
    job_id = request.form.get('job_id')
    position_name = request.form.get('position_name')
    job_description = request.form.get('job_description')

        # Create new applicant
    new_jobrequirement = JobRequirement(
        job_id=job_id,
        position_name=position_name.title(),
        job_description=job_description
        )
        
    try:
        db.session.add(new_jobrequirement)
        db.session.commit()
            
        flash('New job listing successfully created!', 'success')
        current_app.logger.info(f"New job listing (Posting: {new_jobrequirement.position_name.title()}) added by {current_user.username}")
        return redirect(url_for('hr.upload_applicants'))
            
    except IntegrityError as e:
        db.session.rollback()
        if 'job_id' in str(e.orig):
            flash('This job role is already listed.', 'error')
        elif 'job_description' in str(e.orig):
            flash('This job role is already listed.', 'error')
        else:
            flash('Database error. Please try again.', 'error')
        current_app.logger.error(f"IntegrityError creating applicant: {str(e)}")
        return render_template('jobs/addjob.html', form_data=request.form)

    return render_template('jobs/addjob.html')

@bp.route('/joblisiting_update/<int:job_id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def joblisting_update(job_id):
    joblisting = JobRequirement.query.get_or_404(job_id)
    position_name = request.form.get('position_name')
    job_description = request.form.get('job_description')
    
    if not new_password or not confirm_password:
        flash('Both password fields are required', 'error')
        return redirect(url_for('admin.edit_user', user_id=user_id))
    
    joblisting.position_name = position_name
    joblisting.job_description = job_description
    db.session.commit()
    
    current_app.logger.info(f"Details updated for job listing {joblisting.position_name} by Admin {current_user.username}")
    flash('Job listing details updated successfully', 'success')

    if request.referrer.endswith(url_for('main.profile')):
        return redirect(url_for('main.profile', user=current_user))
    else:
        return redirect(url_for('admin.edit_user', user_id=user_id))


@bp.route('/delete_joblisting/<int:job_id>', methods=['POST'])
@no_cache
@login_required
@role_required(*HR_ROLES)
def delete_joblisting(job_id):
    joblisting = JobRequirement.query.get_or_404(job_id)
    db.session.delete(joblisting)
    db.session.commit()
    current_app.logger.info(f"Job listing {joblisting.position_name} deleted by Admin {current_user.username}")
    flash('Job listing deleted successfully', 'success')
    return redirect(url_for('admin.manage_users'))

